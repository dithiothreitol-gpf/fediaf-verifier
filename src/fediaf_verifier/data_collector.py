"""Training data collector for future model fine-tuning.

Collects input/output pairs from AI verification calls, including
both raw and self-verified (corrected) responses. Data is stored as
JSONL files with images deduplicated by content hash.

Usage:
    collector = DataCollector(settings)
    collector.record(
        mode="linguistic",
        model="claude-sonnet-4-20250514",
        prompt="...",
        image_b64="...",
        raw_response={"issues": [...]},
        verified_response={"issues": [...]},  # after self-verify
    )
"""

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger


class DataCollector:
    """Collects AI call data for fine-tuning datasets."""

    def __init__(self, base_dir: str | Path, enabled: bool = True) -> None:
        self.enabled = enabled
        self.base_dir = Path(base_dir)
        self.records_dir = self.base_dir / "records"
        self.images_dir = self.base_dir / "images"

        if self.enabled:
            self.records_dir.mkdir(parents=True, exist_ok=True)
            self.images_dir.mkdir(parents=True, exist_ok=True)
            logger.info("DataCollector active: {}", self.base_dir)

    def record(
        self,
        mode: str,
        model: str,
        prompt: str,
        image_b64: str,
        media_type: str,
        raw_response: dict,
        verified_response: dict | None = None,
    ) -> str | None:
        """Save a single AI call record.

        Args:
            mode: Verification mode (e.g. "linguistic", "claims", "structure").
            model: AI model identifier.
            prompt: The prompt sent to the AI.
            image_b64: Base64-encoded input image.
            media_type: MIME type of the image.
            raw_response: Initial AI response as dict.
            verified_response: Self-verified response as dict (or None).

        Returns:
            Path to the saved record, or None if collection is disabled.
        """
        if not self.enabled:
            return None

        try:
            # Deduplicate image by content hash
            image_hash = hashlib.sha256(image_b64[:10000].encode()).hexdigest()[:16]
            image_ext = _media_type_to_ext(media_type)
            image_filename = f"{image_hash}{image_ext}"
            image_path = self.images_dir / image_filename

            if not image_path.exists():
                import base64

                image_path.write_bytes(base64.b64decode(image_b64))
                logger.debug("Saved training image: {}", image_filename)

            # Determine if self-verify made corrections
            was_corrected = False
            if verified_response is not None:
                was_corrected = _responses_differ(raw_response, verified_response)

            # Build record
            record = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "mode": mode,
                "model": model,
                "prompt": prompt,
                "image_hash": image_hash,
                "image_path": str(image_path.relative_to(self.base_dir)),
                "media_type": media_type,
                "raw_response": raw_response,
                "verified_response": verified_response,
                "was_corrected": was_corrected,
            }

            # Append to daily JSONL file
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            records_file = self.records_dir / f"{today}.jsonl"

            with open(records_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

            logger.info(
                "Training data saved: mode={}, corrected={}, file={}",
                mode,
                was_corrected,
                records_file.name,
            )
            return str(records_file)

        except Exception as e:
            logger.warning("DataCollector.record() failed (non-fatal): {}", e)
            return None

    def get_stats(self) -> dict:
        """Return collection statistics."""
        if not self.enabled or not self.records_dir.exists():
            return {"enabled": False, "total_records": 0}

        total = 0
        corrected = 0
        by_mode: dict[str, int] = {}

        for jsonl_file in self.records_dir.glob("*.jsonl"):
            for line in jsonl_file.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                    total += 1
                    if rec.get("was_corrected"):
                        corrected += 1
                    mode = rec.get("mode", "unknown")
                    by_mode[mode] = by_mode.get(mode, 0) + 1
                except json.JSONDecodeError:
                    pass

        images_count = len(list(self.images_dir.glob("*"))) if self.images_dir.exists() else 0
        images_size_mb = sum(
            f.stat().st_size for f in self.images_dir.glob("*")
        ) / 1_048_576 if self.images_dir.exists() else 0

        return {
            "enabled": True,
            "total_records": total,
            "corrected_records": corrected,
            "correction_rate": f"{corrected / total * 100:.1f}%" if total else "0%",
            "by_mode": by_mode,
            "unique_images": images_count,
            "images_size_mb": round(images_size_mb, 1),
        }

    def export_for_finetuning(self, output_path: str | Path, mode: str | None = None) -> int:
        """Export collected data as fine-tuning JSONL (OpenAI/Anthropic format).

        Uses verified_response as the target. Records without
        verified_response are skipped.

        Args:
            output_path: Path for the output JSONL file.
            mode: Filter by mode (e.g. "linguistic"). None = all modes.

        Returns:
            Number of records exported.
        """
        output_path = Path(output_path)
        count = 0

        with open(output_path, "w", encoding="utf-8") as out:
            for jsonl_file in sorted(self.records_dir.glob("*.jsonl")):
                for line in jsonl_file.read_text(encoding="utf-8").splitlines():
                    if not line.strip():
                        continue
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    if mode and rec.get("mode") != mode:
                        continue

                    verified = rec.get("verified_response")
                    if verified is None:
                        continue

                    # Format as chat-style fine-tuning record
                    ft_record = {
                        "messages": [
                            {
                                "role": "user",
                                "content": rec.get("prompt", ""),
                            },
                            {
                                "role": "assistant",
                                "content": json.dumps(
                                    verified, ensure_ascii=False
                                ),
                            },
                        ],
                        "metadata": {
                            "mode": rec.get("mode"),
                            "model": rec.get("model"),
                            "was_corrected": rec.get("was_corrected", False),
                            "image_hash": rec.get("image_hash"),
                        },
                    }
                    out.write(json.dumps(ft_record, ensure_ascii=False) + "\n")
                    count += 1

        logger.info("Exported {} fine-tuning records to {}", count, output_path)
        return count


def _media_type_to_ext(media_type: str) -> str:
    """Convert MIME type to file extension."""
    mapping = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
        "application/pdf": ".pdf",
    }
    return mapping.get(media_type, ".bin")


def _responses_differ(raw: dict, verified: dict) -> bool:
    """Check if self-verify actually changed the response."""
    # Compare serialized JSON (ignoring key order)
    raw_str = json.dumps(raw, sort_keys=True, ensure_ascii=False)
    ver_str = json.dumps(verified, sort_keys=True, ensure_ascii=False)
    return raw_str != ver_str
