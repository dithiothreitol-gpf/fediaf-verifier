"""Streamlit UI for AI Packaging Designer.

Can be run standalone:  streamlit run src/packaging_designer/app.py
Or embedded in the main BULT QA app via: from packaging_designer.app import main
"""

from __future__ import annotations

import streamlit as st
from loguru import logger

# set_page_config only when running standalone (not embedded)
_STANDALONE = __name__ == "__main__" or "fediaf_verifier" not in str(st.session_state.get("_main_app", ""))
if _STANDALONE:
    try:
        st.set_page_config(
            page_title="AI Packaging Designer",
            page_icon="📦",
            layout="wide",
        )
    except st.errors.StreamlitAPIException:
        pass  # Already set by parent app

from packaging_designer.models.design_elements import DesignAnalysis
from packaging_designer.models.enrichment import ElementPriority, EnrichmentResult
from packaging_designer.models.export_config import ExportConfig, ExportFormat
from packaging_designer.models.package_spec import ProductCategory


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
            "srodowiskowych lub w pliku .env"
        )
        st.stop()
    return AnthropicProvider(api_key=api_key, model="claude-sonnet-4-6")


# ---------------------------------------------------------------------------
# Session state initialization
# ---------------------------------------------------------------------------
def _init_state():
    """Initialize session state with defaults."""
    defaults = {
        "analysis": None,
        "enrichment": None,
        "concept_bytes": None,
        "concept_media_type": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


# ---------------------------------------------------------------------------
# UI Components
# ---------------------------------------------------------------------------


def _render_sidebar() -> tuple[ProductCategory, float, str]:
    """Render sidebar with configuration."""
    with st.sidebar:
        st.title("AI Packaging Designer")
        st.markdown("---")

        category = st.selectbox(
            "Kategoria produktu",
            options=[
                ProductCategory.PET_FOOD,
                ProductCategory.FOOD,
                ProductCategory.COSMETICS,
                ProductCategory.SUPPLEMENTS,
                ProductCategory.OTHER,
            ],
            format_func=lambda c: {
                ProductCategory.PET_FOOD: "Karma dla zwierzat",
                ProductCategory.FOOD: "Zywnosc",
                ProductCategory.COSMETICS: "Kosmetyki",
                ProductCategory.SUPPLEMENTS: "Suplementy",
                ProductCategory.OTHER: "Inne",
            }.get(c, c.value),
        )

        bleed_mm = st.number_input(
            "Spad (mm)", value=3.0, min_value=0.0, max_value=10.0, step=0.5
        )

        export_format = st.radio(
            "Format wyjsciowy",
            options=["Illustrator (.jsx)", "JSX + podglad PNG"],
            index=1,
        )

        st.markdown("---")
        st.markdown(
            "**Instrukcja:**\n"
            "1. Zaladuj grafike koncepcyjna\n"
            "2. Kliknij 'Analizuj'\n"
            "3. Zaznacz brakujace elementy\n"
            "4. Pobierz pakiet ZIP\n"
            "5. Uruchom .jsx w Illustratorze"
        )
        st.caption("v0.1.0 MVP")

        return category, bleed_mm, export_format


def _render_analysis_results(analysis: DesignAnalysis):
    """Render analysis results."""
    spec = analysis.package_spec

    # Header metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Typ", spec.package_type.value)
    col2.metric(
        "Wymiary",
        f"{spec.dimensions.width_mm:.0f} x {spec.dimensions.height_mm:.0f} mm",
    )
    col3.metric("Kategoria", spec.product_category.value)
    col4.metric("Stron", spec.sides_visible)

    if spec.product_name or spec.brand_name:
        st.info(
            f"**Produkt:** {spec.product_name or '—'}  |  "
            f"**Marka:** {spec.brand_name or '—'}"
        )

    # Colors
    if analysis.color_swatches:
        st.markdown("**Paleta kolorow CMYK:**")
        cols = st.columns(min(len(analysis.color_swatches), 8))
        for i, swatch in enumerate(analysis.color_swatches[:8]):
            with cols[i]:
                st.color_picker(
                    swatch.name,
                    value=swatch.hex,
                    disabled=True,
                    key=f"cp_{i}",
                )
                st.caption(
                    f"C:{swatch.cyan:.0f} M:{swatch.magenta:.0f} "
                    f"Y:{swatch.yellow:.0f} K:{swatch.key:.0f}"
                )

    # Texts
    if analysis.text_blocks:
        with st.expander(f"Wykryte teksty ({len(analysis.text_blocks)})", expanded=True):
            for tb in analysis.text_blocks:
                st.markdown(
                    f"- **[{tb.role}]** {tb.content[:80]}"
                    f" — *{tb.font_style}, {tb.font_size_pt or '?'}pt*"
                )

    # Graphics
    if analysis.graphic_regions:
        with st.expander(
            f"Elementy graficzne ({len(analysis.graphic_regions)})"
        ):
            for gr in analysis.graphic_regions:
                st.markdown(f"- **[{gr.region_type}]** {gr.description[:80]}")

    # Existing elements
    if analysis.existing_elements:
        st.markdown(
            "**Wykryte elementy regulacyjne:** "
            + ", ".join(f"`{e}`" for e in analysis.existing_elements)
        )

    # AI summary
    if analysis.ai_summary:
        with st.expander("Podsumowanie AI"):
            st.write(analysis.ai_summary)


def _render_enrichment_ui(analysis: DesignAnalysis) -> tuple[list[str], str | None]:
    """Render enrichment checkboxes and return selections."""
    from packaging_designer.enricher import detect_missing_elements

    missing = detect_missing_elements(analysis)

    if not missing:
        st.success("Wszystkie wymagane elementy wykryte na opakowaniu.")
        return [], None

    selected = []
    ean_number = None

    for elem in missing:
        icon = {
            ElementPriority.MANDATORY: "🔴",
            ElementPriority.RECOMMENDED: "🟡",
            ElementPriority.OPTIONAL: "⚪",
        }.get(elem.priority, "")

        default_on = elem.priority in (
            ElementPriority.MANDATORY,
            ElementPriority.RECOMMENDED,
        )

        checked = st.checkbox(
            f"{icon} {elem.display_name} ({elem.priority.value})",
            value=default_on,
            help=f"{elem.description}" + (f"\n{elem.regulation}" if elem.regulation else ""),
            key=f"enr_{elem.element_id}",
        )
        if checked:
            selected.append(elem.element_id)

            if elem.element_id == "ean_barcode":
                ean_number = st.text_input(
                    "Numer EAN-13",
                    placeholder="5901234123457",
                    key="ean_input",
                )

    return selected, ean_number


def _render_export(
    analysis: DesignAnalysis,
    enrichment: EnrichmentResult | None,
    concept_bytes: bytes | None,
    export_format: str,
    bleed_mm: float,
):
    """Render export section with download buttons."""
    from packaging_designer.builders.jsx_builder import build_jsx
    from packaging_designer.models.export_config import ExportConfig
    from packaging_designer.pipeline import create_jsx_package

    config = ExportConfig(bleed_mm=bleed_mm)

    jsx_content = build_jsx(
        analysis=analysis,
        enrichment=enrichment,
        config=config,
        include_concept=concept_bytes is not None,
    )

    # Create ZIP package
    zip_bytes = create_jsx_package(
        jsx_content=jsx_content,
        enrichment=enrichment,
        concept_image=concept_bytes,
    )

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="Pobierz pakiet Illustrator (.zip)",
            data=zip_bytes,
            file_name="packaging_design_ai.zip",
            mime="application/zip",
            type="primary",
            use_container_width=True,
        )
        st.caption(
            "Zawiera: `packaging_design.jsx` + `assets/`\n\n"
            "Uruchom w Illustratorze: **File > Scripts > Other Script...**"
        )

    with col2:
        st.download_button(
            label="Pobierz sam skrypt .jsx",
            data=jsx_content,
            file_name="packaging_design.jsx",
            mime="text/plain",
            use_container_width=True,
        )

    # Preview
    if "PNG" in export_format:
        from packaging_designer.builders.preview_builder import build_preview_png

        try:
            preview_bytes = build_preview_png(
                analysis=analysis, concept_image=concept_bytes
            )
            st.image(preview_bytes, caption="Podglad z zaznaczonymi elementami")
        except Exception as e:
            st.warning(f"Nie udalo sie wygenerowac podgladu: {e}")

    # Show JSX preview
    with st.expander("Podglad skryptu JSX"):
        st.code(jsx_content[:3000] + "\n// ... (skrocone)", language="javascript")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    _init_state()
    category, bleed_mm, export_format = _render_sidebar()

    st.title("AI Packaging Designer")
    st.markdown(
        "Zaladuj grafike koncepcyjna opakowania — narzedzie zanalizuje ja, "
        "zidentyfikuje elementy i wygeneruje roboczy plik DTP."
    )

    # --- STEP 1: Upload ---
    col_upload, col_ctx = st.columns([2, 1])
    with col_upload:
        uploaded = st.file_uploader(
            "Grafika koncepcyjna",
            type=["png", "jpg", "jpeg", "pdf", "webp"],
            help="PNG/JPG/PDF — koncept wygenerowany przez AI lub mockup",
        )
    with col_ctx:
        product_context = st.text_area(
            "Kontekst produktu (opcjonalnie)",
            placeholder="Np. Karma mokra dla kotow, 85g saszetka, marka XYZ...",
            height=100,
        )

    if not uploaded:
        st.info("Zaladuj grafike koncepcyjna aby rozpoczac.")
        return

    # Read and cache file bytes
    concept_bytes = uploaded.read()
    media_type = uploaded.type or "image/png"
    st.session_state.concept_bytes = concept_bytes
    st.session_state.concept_media_type = media_type

    # Show uploaded image
    st.image(concept_bytes, caption="Zaladowana grafika", width=400)

    # --- STEP 2: Analysis ---
    if st.button("Analizuj grafike", type="primary", use_container_width=True):
        with st.spinner("Analizuje z Claude Vision..."):
            try:
                provider = _get_provider()
                from packaging_designer.pipeline import run_analysis

                analysis = run_analysis(
                    image_bytes=concept_bytes,
                    media_type=media_type,
                    provider=provider,
                    product_context=product_context,
                )
                st.session_state.analysis = analysis
                st.session_state.enrichment = None  # reset enrichment
                st.rerun()
            except Exception as e:
                logger.exception("Analysis failed")
                st.error(f"Blad analizy: {e}")
                return

    analysis: DesignAnalysis | None = st.session_state.analysis
    if not analysis:
        return

    # --- STEP 3: Display results ---
    st.markdown("---")
    st.subheader("Wyniki analizy")
    _render_analysis_results(analysis)

    # --- STEP 4: Enrichment ---
    st.markdown("---")
    st.subheader("Brakujace elementy")
    selected_ids, ean_number = _render_enrichment_ui(analysis)

    if selected_ids:
        if st.button("Generuj brakujace elementy", use_container_width=True):
            from packaging_designer.pipeline import run_enrichment

            enrichment = run_enrichment(
                analysis=analysis,
                selected_ids=selected_ids,
                ean_number=ean_number,
            )
            st.session_state.enrichment = enrichment
            st.success(
                f"Wygenerowano {len(enrichment.generated_assets)} assetow"
            )

    # --- STEP 5: Export ---
    st.markdown("---")
    st.subheader("Eksport DTP")
    _render_export(
        analysis=analysis,
        enrichment=st.session_state.enrichment,
        concept_bytes=concept_bytes,
        export_format=export_format,
        bleed_mm=bleed_mm,
    )


if __name__ == "__main__":
    main()
