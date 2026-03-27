"""Streamlit UI for Catalog Translator.

Can be run standalone:  streamlit run src/catalog_translator/app.py
Or embedded in the main BULT QA app via: from catalog_translator.app import main
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st
from loguru import logger

# set_page_config only when running standalone
try:
    st.set_page_config(
        page_title="Catalog Translator",
        page_icon="\U0001f4d1",
        layout="wide",
    )
except st.errors.StreamlitAPIException:
    pass  # Already set by parent app (embedded mode)


# ---------------------------------------------------------------------------
# Languages (used in standalone mode only)
# ---------------------------------------------------------------------------
_TRANSLATION_LANGUAGES: dict[str, str] = {
    "de": "Deutsch",
    "en": "English",
    "fr": "Fran\u00e7ais",
    "es": "Espa\u00f1ol",
    "it": "Italiano",
    "nl": "Nederlands",
    "cs": "\u010ce\u0161tina",
    "sk": "Sloven\u010dina",
    "sv": "Svenska",
    "da": "Dansk",
    "pt": "Portugu\u00eas",
    "hu": "Magyar",
    "ro": "Rom\u00e2n\u0103",
    "pl": "Polski",
}


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------
def _get_provider():
    """Get AI provider — reuses fediaf_verifier config when available."""
    try:
        from fediaf_verifier.config import get_settings
        from fediaf_verifier.verifier import create_providers

        settings = get_settings()
        extraction_provider, _ = create_providers(settings)
        return extraction_provider
    except Exception:
        pass

    # Fallback: direct Anthropic provider from env
    import os

    from fediaf_verifier.providers import AnthropicProvider

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("ANTHROPIC_API_KEY="):
                        api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
    if not api_key:
        st.error(
            "Brak klucza API. Ustaw ANTHROPIC_API_KEY w zmiennych "
            "\u015brodowiskowych lub w pliku .env"
        )
        st.stop()
    return AnthropicProvider(api_key=api_key, model="claude-sonnet-4-6")


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
def _init_state() -> None:
    defaults = {
        "ct_extraction": None,
        "ct_structured": None,
        "ct_batches": None,
        "ct_validation": None,
        "ct_loaded_glossary": None,
        "ct_pdf_bytes": None,
        "ct_filename": "",
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main(
    target_lang: str = "de",
    target_lang_name: str = "Deutsch",
    page_range: str = "all",
    dry_run: bool = False,
    run_validation: bool = True,
    glossary_file: object | None = None,
) -> None:
    """Catalog Translator entry point.

    When embedded, all sidebar options are passed as arguments from the main app.
    When standalone, a sidebar is rendered locally.
    """
    _init_state()

    # Standalone mode: render sidebar if no args were explicitly passed
    _is_standalone = target_lang == "de" and not st.session_state.get("_ct_embedded")
    # Mark as embedded when called with explicit params from main app
    if not _is_standalone:
        st.session_state["_ct_embedded"] = True

    st.header("\U0001f4d1 T\u0142umaczenie katalogu produktowego")
    st.caption(
        "Wgraj wielostronicowy PDF katalogu \u2192 ekstrakcja tekstu \u2192 "
        "t\u0142umaczenie partiami \u2192 eksport do XLSX"
    )

    # ── File upload ──────────────────────────────────────────────────────
    uploaded = st.file_uploader(
        "Wgraj katalog PDF",
        type=["pdf"],
        help="Wielostronicowy PDF katalogu produktowego",
        key="ct_pdf_upload",
    )

    if uploaded:
        col_info, col_action = st.columns([2, 1])
        with col_info:
            st.markdown(f"**Plik:** {uploaded.name}")
            st.markdown(f"**Rozmiar:** {uploaded.size / 1024:.1f} KB")

        # Store PDF bytes
        uploaded.seek(0)
        st.session_state.ct_pdf_bytes = uploaded.read()
        st.session_state.ct_filename = uploaded.name

    # ── Step 1: Extract ──────────────────────────────────────────────────
    if st.session_state.ct_pdf_bytes is not None:
        st.divider()

        if st.button(
            "\U0001f50d Ekstrahuj tekst z PDF",
            type="secondary",
            width="stretch",
        ):
            from .extractor import extract_catalog
            from .glossary import load_default_glossary, load_glossary_from_bytes
            from .structurer import structure_catalog

            with st.spinner("Ekstrakcja tekstu z PDF..."):
                try:
                    extraction = extract_catalog(
                        pdf_bytes=st.session_state.ct_pdf_bytes,
                        page_range=page_range,
                        source_filename=st.session_state.ct_filename,
                    )
                    st.session_state.ct_extraction = extraction
                except Exception as exc:
                    st.error(f"B\u0142\u0105d ekstrakcji: {exc}")
                    logger.exception("Extraction failed")
                    return

            with st.spinner("Strukturyzacja tekstu..."):
                structured = structure_catalog(extraction)
                st.session_state.ct_structured = structured

            # Load glossary
            if glossary_file is not None:
                glossary_file.seek(0)
                glossary = load_glossary_from_bytes(glossary_file.read())
            else:
                glossary = load_default_glossary(target_lang)
            st.session_state.ct_loaded_glossary = glossary

            # Reset downstream
            st.session_state.ct_batches = None
            st.session_state.ct_validation = None

            st.rerun()

    # ── Show extraction results ──────────────────────────────────────────
    if st.session_state.ct_extraction is not None:
        extraction = st.session_state.ct_extraction
        structured = st.session_state.ct_structured

        st.divider()
        st.subheader("Wynik ekstrakcji")

        total_blocks = sum(len(p.blocks) for p in extraction.pages)
        total_units = sum(len(p) for p in structured) if structured else 0

        m1, m2, m3 = st.columns(3)
        m1.metric("Stron z tre\u015bci\u0105", len(extraction.pages))
        m2.metric("Bloki tekstu", total_blocks)
        m3.metric("Jednostki t\u0142umaczeniowe", total_units)

        if structured:
            with st.expander("Podgl\u0105d jednostek t\u0142umaczeniowych", expanded=False):
                for page_units in structured:
                    if not page_units:
                        continue
                    page_num = page_units[0].page_number
                    section = page_units[0].section_name or "\u2014"
                    st.markdown(f"**Strona {page_num}** \u2014 {section}")

                    rows = []
                    for u in page_units:
                        rows.append({
                            "ID": u.unit_id,
                            "Kategoria": u.category.value,
                            "J\u0119zyk": u.detected_language,
                            "Tekst": u.source_text[:80] + ("..." if len(u.source_text) > 80 else ""),
                        })
                    st.dataframe(rows, width="stretch", hide_index=True)

    # ── Step 2: Translate ────────────────────────────────────────────────
    if st.session_state.ct_structured is not None and not dry_run:
        st.divider()

        structured = st.session_state.ct_structured
        total_pages = len(structured)

        if st.session_state.ct_batches is None:
            if st.button(
                f"\U0001f30d Przet\u0142umacz na {target_lang_name} ({total_pages} stron)",
                type="primary",
                width="stretch",
            ):
                from .translator import translate_catalog

                provider = _get_provider()
                progress_bar = st.progress(0, text="T\u0142umacz\u0119...")
                status_text = st.empty()

                def _on_progress(done: int, total: int) -> None:
                    progress_bar.progress(
                        done / total,
                        text=f"T\u0142umacz\u0119 stron\u0119 {done}/{total}...",
                    )
                    status_text.caption(f"Uko\u0144czono {done} z {total} partii")

                try:
                    batches = translate_catalog(
                        pages=structured,
                        target_lang=target_lang,
                        target_lang_name=target_lang_name,
                        glossary=st.session_state.ct_loaded_glossary,
                        provider=provider,
                        max_tokens=8192,
                        progress_callback=_on_progress,
                    )
                    st.session_state.ct_batches = batches
                except Exception as exc:
                    st.error(f"B\u0142\u0105d t\u0142umaczenia: {exc}")
                    logger.exception("Translation failed")
                    return

                # Auto-validate
                if run_validation:
                    from .validator import validate_catalog

                    validation = validate_catalog(
                        pages=structured,
                        batches=batches,
                        glossary=st.session_state.ct_loaded_glossary,
                        target_lang=target_lang,
                    )
                    st.session_state.ct_validation = validation

                st.rerun()

    # ── Show translation results ─────────────────────────────────────────
    if st.session_state.ct_batches is not None:
        batches = st.session_state.ct_batches
        structured = st.session_state.ct_structured

        st.divider()
        st.subheader("Wynik t\u0142umaczenia")

        translated_count = sum(
            len([u for u in b.units if u.translated_text])
            for b in batches
            if not b.error
        )
        failed_count = sum(1 for b in batches if b.error)
        total_units = sum(len(p) for p in structured) if structured else 0

        m1, m2, m3 = st.columns(3)
        m1.metric("Przet\u0142umaczono", translated_count)
        m2.metric("B\u0142\u0119dne partie", failed_count)
        m3.metric("\u0141\u0105cznie jednostek", total_units)

        # Show batches
        for batch in batches:
            label = f"Strona {batch.page_number}"
            if batch.section_name:
                label += f" \u2014 {batch.section_name}"
            if batch.error:
                label += " \u274c"
            else:
                label += f" ({len(batch.units)} elem.)"

            with st.expander(label, expanded=False):
                if batch.error:
                    st.error(batch.error)
                    continue

                for tu in batch.units:
                    col_src, col_tgt = st.columns(2)
                    with col_src:
                        st.markdown(f"**[{tu.category.value}]** {tu.source_text}")
                    with col_tgt:
                        st.markdown(tu.translated_text or "*\u2014 brak \u2014*")
                    if tu.note_for_designer:
                        st.caption(f"\U0001f4dd {tu.note_for_designer}")

        # ── Validation ───────────────────────────────────────────────────
        validation = st.session_state.ct_validation
        if validation:
            st.divider()
            st.subheader("Walidacja")

            v1, v2, v3 = st.columns(3)
            v1.metric("Sprawdzono", validation.total_checked)
            v2.metric("B\u0142\u0119dy", validation.errors_count)
            v3.metric("Ostrze\u017cenia", validation.warnings_count)

            if validation.issues:
                with st.expander(
                    f"Szczeg\u00f3\u0142y ({len(validation.issues)} problem\u00f3w)",
                    expanded=False,
                ):
                    rows = []
                    for issue in validation.issues:
                        rows.append({
                            "Strona": issue.page,
                            "Typ": issue.check_type,
                            "Wa\u017cno\u015b\u0107": issue.severity.value,
                            "Wiadomo\u015b\u0107": issue.message,
                        })
                    st.dataframe(rows, width="stretch", hide_index=True)

        # ── Export XLSX ──────────────────────────────────────────────────
        st.divider()

        from .exporter import export_xlsx

        xlsx_bytes = export_xlsx(
            batches=batches,
            pages=structured,
            validation=validation,
            glossary=st.session_state.ct_loaded_glossary,
            target_lang=target_lang,
            source_filename=st.session_state.ct_filename,
        )

        stem = Path(st.session_state.ct_filename).stem
        xlsx_name = f"{stem}_translation_{target_lang}.xlsx"

        st.download_button(
            "\u2b07\ufe0f Pobierz XLSX",
            data=xlsx_bytes,
            file_name=xlsx_name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            width="stretch",
        )

    # ── Dry run info ─────────────────────────────────────────────────────
    if dry_run and st.session_state.ct_structured is not None:
        st.info(
            "Tryb dry-run: ekstrakcja i strukturyzacja zako\u0144czona. "
            "Wy\u0142\u0105cz dry-run, aby uruchomi\u0107 t\u0142umaczenie."
        )


# ---------------------------------------------------------------------------
# Standalone entry — renders its own sidebar
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    with st.sidebar:
        st.subheader("Opcje t\u0142umaczenia katalogu")
        _tl_display = [f"{name} ({code})" for code, name in _TRANSLATION_LANGUAGES.items()]
        _tl_selection = st.selectbox("J\u0119zyk docelowy", _tl_display, index=0)
        _tl_idx = _tl_display.index(_tl_selection)
        _tl_codes = list(_TRANSLATION_LANGUAGES.keys())
        _target_lang = _tl_codes[_tl_idx]
        _target_name = list(_TRANSLATION_LANGUAGES.values())[_tl_idx]
        st.divider()
        _glossary_file = st.file_uploader("S\u0142ownik (opcjonalnie)", type=["json"])
        _page_range = st.text_input("Zakres stron", value="all")
        _dry_run = st.checkbox("Dry run", value=False)
        _validate = st.checkbox("Walidacja", value=True)

    main(
        target_lang=_target_lang,
        target_lang_name=_target_name,
        page_range=_page_range,
        dry_run=_dry_run,
        run_validation=_validate,
        glossary_file=_glossary_file,
    )
