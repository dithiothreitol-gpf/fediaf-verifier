"""Optional dependency checker and in-app installer for Streamlit UI.

Provides functions to check if optional packages are available and
install them on demand via pip subprocess (with user consent in UI).
"""

from __future__ import annotations

import importlib
import subprocess
import sys
from dataclasses import dataclass

from loguru import logger


@dataclass
class OptionalFeature:
    """Describes an optional feature with its required packages."""

    name: str
    description: str
    packages: list[str]
    pip_extra: str  # e.g. "ocr" → pip install fediaf-verifier[ocr]
    import_check: str  # module to import to verify availability
    size_hint: str  # approximate download size


# Registry of optional features
OPTIONAL_FEATURES: dict[str, OptionalFeature] = {
    "ocr": OptionalFeature(
        name="OCR Text Comparison",
        description=(
            "Porownanie tekstu miedzy wersjami etykiety za pomoca OCR "
            "(EasyOCR — 80+ jezykow). Wymaga ~200MB pobrania przy "
            "pierwszej instalacji."
        ),
        packages=["easyocr"],
        pip_extra="ocr",
        import_check="easyocr",
        size_hint="~200 MB",
    ),
    "saliency": OptionalFeature(
        name="Analiza uwagi wizualnej",
        description=(
            "Heatmapa predykcji uwagi konsumenta (DeepGaze IIE). "
            "Wymaga PyTorch — ~800MB pobrania. Bez tego modulu "
            "analiza uwagi uzywa lekkich heurystyk."
        ),
        packages=["deepgaze-pytorch", "torch", "scipy"],
        pip_extra="saliency",
        import_check="deepgaze_pytorch",
        size_hint="~800 MB",
    ),
    "pdf": OptionalFeature(
        name="Zaawansowana analiza PDF",
        description=(
            "Analiza fontow, bleedu i ICC w plikach PDF (PyMuPDF). "
            "Wymaga ~30MB pobrania."
        ),
        packages=["pymupdf"],
        pip_extra="annotation",
        import_check="fitz",
        size_hint="~30 MB",
    ),
}


def is_available(feature_key: str) -> bool:
    """Check if an optional feature's dependencies are installed."""
    feat = OPTIONAL_FEATURES.get(feature_key)
    if not feat:
        return False
    try:
        importlib.import_module(feat.import_check)
        return True
    except ImportError:
        return False


def check_all() -> dict[str, bool]:
    """Check availability of all optional features."""
    return {key: is_available(key) for key in OPTIONAL_FEATURES}


def install_feature(feature_key: str) -> tuple[bool, str]:
    """Install an optional feature via pip.

    Returns:
        Tuple of (success: bool, message: str).
    """
    feat = OPTIONAL_FEATURES.get(feature_key)
    if not feat:
        return False, f"Nieznana funkcja: {feature_key}"

    packages = feat.packages
    logger.info("Instaluje pakiety: {}", packages)

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", *packages],
            capture_output=True,
            text=True,
            timeout=600,  # 10 min max
        )
        if result.returncode == 0:
            logger.info("Instalacja udana: {}", packages)
            # Clear import caches so Python discovers newly installed packages
            importlib.invalidate_caches()
            # Verify import works
            try:
                importlib.import_module(feat.import_check)
                return True, f"Zainstalowano: {', '.join(packages)}"
            except ImportError as e:
                return False, f"Pakiety zainstalowane ale import nieudany: {e}"
        else:
            error_msg = result.stderr[-500:] if result.stderr else "nieznany blad"
            logger.error("Instalacja nieudana: {}", error_msg)
            return False, f"Blad instalacji: {error_msg}"
    except subprocess.TimeoutExpired:
        return False, "Instalacja przekroczyla limit czasu (10 min)"
    except Exception as e:
        return False, f"Blad: {e}"


def render_feature_manager() -> None:
    """Render optional features manager in Streamlit sidebar."""
    import streamlit as st

    status = check_all()
    has_missing = any(not v for v in status.values())

    if not has_missing:
        return  # All features installed, nothing to show

    with st.expander("\u2699\ufe0f Dodatkowe funkcje", expanded=False):
        st.caption(
            "Niektore funkcje wymagaja dodatkowych pakietow. "
            "Kliknij aby zainstalowac."
        )

        for key, feat in OPTIONAL_FEATURES.items():
            installed = status[key]

            if installed:
                st.markdown(f"\u2705 **{feat.name}**")
            else:
                st.markdown(f"\u274c **{feat.name}** ({feat.size_hint})")
                st.caption(feat.description)
                if st.button(
                    f"\U0001f4e5 Instaluj {feat.name}",
                    key=f"install_{key}",
                    use_container_width=True,
                ):
                    with st.spinner(
                        f"Instaluje {feat.name}... "
                        f"To moze potrwac kilka minut."
                    ):
                        ok, msg = install_feature(key)
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                st.divider()


def render_missing_feature_banner(feature_key: str) -> bool:
    """Show an inline banner when a feature is missing.

    Returns True if the feature IS available (caller should proceed).
    Returns False if missing (caller should skip/degrade).
    """
    import streamlit as st

    if is_available(feature_key):
        return True

    feat = OPTIONAL_FEATURES.get(feature_key)
    if not feat:
        return False

    st.info(
        f"\U0001f4e6 **{feat.name}** wymaga dodatkowej instalacji ({feat.size_hint}).\n\n"
        f"{feat.description}"
    )

    if st.button(
        f"Zainstaluj {feat.name}",
        key=f"inline_install_{feature_key}",
        type="primary",
    ):
        with st.spinner(
            f"Instaluje {feat.name}... To moze potrwac kilka minut."
        ):
            ok, msg = install_feature(feature_key)
        if ok:
            st.success(msg)
            st.rerun()
        else:
            st.error(msg)

    return False
