"""Streamlit UI for AI Packaging Designer.

Can be run standalone:  streamlit run src/packaging_designer/app.py
Or embedded in the main BULT QA app via: from packaging_designer.app import main
"""

from __future__ import annotations

import streamlit as st
from loguru import logger

# set_page_config only when running standalone — when embedded,
# the parent app already called set_page_config
try:
    st.set_page_config(
        page_title="AI Packaging Designer",
        page_icon="\U0001f4e6",
        layout="wide",
    )
except st.errors.StreamlitAPIException:
    pass  # Already set by parent app (embedded mode)

from packaging_designer.models.design_elements import DesignAnalysis
from packaging_designer.models.enrichment import ElementPriority, EnrichmentResult
from packaging_designer.models.export_config import ExportConfig, ExportFormat
from packaging_designer.models.package_spec import ProductCategory


def _get_provider():
    """Get AI provider \u2014 reuses fediaf_verifier config when available."""
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
# Session state initialization
# ---------------------------------------------------------------------------
def _init_state():
    """Initialize session state with defaults."""
    defaults = {
        "pkg_analysis": None,
        "pkg_enrichment": None,
        "pkg_concept_bytes": None,
        "pkg_media_type": None,
        "pkg_back_label": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


# ---------------------------------------------------------------------------
# UI Components
# ---------------------------------------------------------------------------


def _render_sidebar() -> tuple[ProductCategory, float, str, bool]:
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
                ProductCategory.PET_FOOD: "Karma dla zwierz\u0105t",
                ProductCategory.FOOD: "\u017bywno\u015b\u0107",
                ProductCategory.COSMETICS: "Kosmetyki",
                ProductCategory.SUPPLEMENTS: "Suplementy",
                ProductCategory.OTHER: "Inne",
            }.get(c, c.value),
        )

        bleed_mm = st.number_input(
            "Spad (mm)", value=3.0, min_value=0.0, max_value=10.0, step=0.5
        )

        export_format = st.radio(
            "Format wyj\u015bciowy",
            options=[
                "Illustrator (.jsx)",
                "InDesign (.idml)",
                "Oba (Illustrator + InDesign)",
            ],
            index=0,
        )

        st.markdown("---")
        st.markdown(
            "**Instrukcja:**\n"
            "1. Za\u0142aduj grafik\u0119 koncepcyjn\u0105\n"
            "2. Kliknij \u201eAnalizuj\u201d\n"
            "3. Zaznacz brakuj\u0105ce elementy\n"
            "4. Opcjonalnie: back label, dieline, 3D\n"
            "5. Pobierz pakiet ZIP\n"
            "6. Uruchom .jsx w AI / otw\u00f3rz .idml w ID"
        )

        st.markdown("---")
        batch_mode = st.toggle("Tryb wsadowy (batch)", key="batch_mode_toggle")
        st.caption("v0.2.0")

        return category, bleed_mm, export_format, batch_mode


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
            f"**Produkt:** {spec.product_name or '\u2014'}  |  "
            f"**Marka:** {spec.brand_name or '\u2014'}"
        )

    # Colors
    if analysis.color_swatches:
        st.markdown("**Paleta kolor\u00f3w CMYK:**")
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
                    f" \u2014 *{tb.font_style}, {tb.font_size_pt or '?'}pt*"
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
            ElementPriority.MANDATORY: "\U0001f534",
            ElementPriority.RECOMMENDED: "\U0001f7e1",
            ElementPriority.OPTIONAL: "\u26aa",
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
    from packaging_designer.models.export_config import ExportConfig, ExportFormat

    want_jsx = "Illustrator" in export_format or "Oba" in export_format
    want_idml = "InDesign" in export_format or "Oba" in export_format

    # --- Illustrator JSX ---
    if want_jsx:
        from packaging_designer.builders.jsx_builder import build_jsx
        from packaging_designer.pipeline import create_jsx_package

        config = ExportConfig(bleed_mm=bleed_mm)
        jsx_content = build_jsx(
            analysis=analysis,
            enrichment=enrichment,
            config=config,
            include_concept=concept_bytes is not None,
        )
        zip_bytes = create_jsx_package(
            jsx_content=jsx_content,
            enrichment=enrichment,
            concept_image=concept_bytes,
        )

        st.markdown("#### Illustrator")
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="\u2b07\ufe0f Pobierz pakiet Illustrator (.zip)",
                data=zip_bytes,
                file_name="packaging_design_ai.zip",
                mime="application/zip",
                type="primary",
                width="stretch",
            )
            st.caption(
                "Zawiera: `packaging_design.jsx` + `assets/`\n\n"
                "Uruchom: **File > Scripts > Other Script...**"
            )
        with col2:
            st.download_button(
                label="\U0001f4c4 Sam skrypt .jsx",
                data=jsx_content,
                file_name="packaging_design.jsx",
                mime="text/plain",
                width="stretch",
            )

        with st.expander("Podgl\u0105d JSX"):
            st.code(jsx_content[:2000] + "\n// ...", language="javascript")

    # --- InDesign IDML ---
    if want_idml:
        from packaging_designer.builders.idml_builder import build_idml

        config_idml = ExportConfig(bleed_mm=bleed_mm)
        idml_bytes = build_idml(
            analysis=analysis,
            enrichment=enrichment,
            config=config_idml,
        )

        st.markdown("#### InDesign")
        st.download_button(
            label="\u2b07\ufe0f Pobierz plik InDesign (.idml)",
            data=idml_bytes,
            file_name="packaging_design.idml",
            mime="application/vnd.adobe.indesign-idml-package",
            type="primary" if not want_jsx else "secondary",
            width="stretch",
        )
        st.caption(
            "Otw\u00f3rz bezpo\u015brednio w InDesign (CS4+).\n\n"
            "Plik zawiera: warstwy, kolory CMYK, ramki tekstowe, wymiary strony."
        )

    # --- Preview ---
    from packaging_designer.builders.preview_builder import build_preview_png

    try:
        preview_bytes = build_preview_png(
            analysis=analysis, concept_image=concept_bytes
        )
        st.image(preview_bytes, caption="Podgl\u0105d z zaznaczonymi elementami")
    except Exception as e:
        st.warning(f"Podgl\u0105d niedost\u0119pny: {e}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def _render_batch_ui(export_format: str, bleed_mm: float):
    """Render batch processing UI."""
    st.subheader("Tryb wsadowy")
    st.markdown("Za\u0142aduj wiele grafik koncepcyjnych \u2014 ka\u017cda zostanie przetworzona osobno.")

    batch_files = st.file_uploader(
        "Grafiki koncepcyjne",
        type=["png", "jpg", "jpeg"],
        accept_multiple_files=True,
        key="batch_files",
    )

    if not batch_files:
        st.info("Za\u0142aduj pliki, aby rozpocz\u0105\u0107 przetwarzanie wsadowe.")
        return

    st.write(f"Za\u0142adowano {len(batch_files)} plik\u00f3w")

    gen_jsx = "Illustrator" in export_format or "Oba" in export_format
    gen_idml = "InDesign" in export_format or "Oba" in export_format

    if st.button("Przetw\u00f3rz wsadowo", type="primary", width="stretch"):
        from packaging_designer.batch import BatchItem, package_batch_results, run_batch

        items = []
        for f in batch_files:
            raw = f.read()
            items.append(BatchItem(
                filename=f.name,
                image_bytes=raw,
                media_type=f.type or "image/png",
            ))

        progress = st.progress(0, text="Przetwarzanie\u2026")

        def on_progress(current, total, name):
            progress.progress(current / total, text=f"[{current}/{total}] {name}")

        try:
            provider = _get_provider()
            results = run_batch(
                items=items,
                provider=provider,
                generate_jsx=gen_jsx,
                generate_idml=gen_idml,
                bleed_mm=bleed_mm,
                on_progress=on_progress,
            )

            ok = sum(1 for r in results if r.success)
            fail = sum(1 for r in results if not r.success)
            st.success(f"Gotowe: {ok} sukces\u00f3w, {fail} b\u0142\u0119d\u00f3w")

            zip_bytes = package_batch_results(
                results, include_jsx=gen_jsx, include_idml=gen_idml,
            )
            st.download_button(
                label=f"Pobierz wyniki ({ok} plik\u00f3w)",
                data=zip_bytes,
                file_name="batch_packaging_output.zip",
                mime="application/zip",
                type="primary",
                width="stretch",
            )

        except Exception as e:
            logger.exception("Batch failed")
            st.error(f"B\u0142\u0105d: {e}")


def main():
    _init_state()
    category, bleed_mm, export_format, batch_mode = _render_sidebar()

    st.title("AI Packaging Designer")
    st.markdown(
        "Za\u0142aduj grafik\u0119 koncepcyjn\u0105 opakowania \u2014 narz\u0119dzie zanalizuje j\u0105, "
        "zidentyfikuje elementy i wygeneruje roboczy plik DTP."
    )

    # --- BATCH MODE ---
    if batch_mode:
        _render_batch_ui(export_format, bleed_mm)
        return

    # --- STEP 1: Upload ---
    col_upload, col_ctx = st.columns([2, 1])
    with col_upload:
        uploaded = st.file_uploader(
            "Grafika koncepcyjna",
            type=["png", "jpg", "jpeg", "pdf", "webp"],
            help="PNG/JPG/PDF \u2014 koncept wygenerowany przez AI lub mockup",
        )
    with col_ctx:
        product_context = st.text_area(
            "Kontekst produktu (opcjonalnie)",
            placeholder="Np. Karma mokra dla kot\u00f3w, 85g saszetka, marka XYZ...",
            height=100,
        )

    if uploaded:
        # Cache file bytes in session state so they survive reruns
        raw = uploaded.read()
        if raw:
            st.session_state.pkg_concept_bytes = raw
            st.session_state.pkg_media_type = uploaded.type or "image/png"

    concept_bytes: bytes | None = st.session_state.get("pkg_concept_bytes")
    media_type: str = st.session_state.get("pkg_media_type", "image/png")

    if not concept_bytes:
        st.info("Za\u0142aduj grafik\u0119 koncepcyjn\u0105, aby rozpocz\u0105\u0107.")
        return

    # Show uploaded image
    st.image(concept_bytes, caption="Za\u0142adowana grafika", width=400)

    # --- STEP 2: Analysis ---
    if st.button("Analizuj grafik\u0119", type="primary", width="stretch"):
        with st.spinner("Analizowanie z AI\u2026"):
            try:
                provider = _get_provider()
                from packaging_designer.pipeline import run_analysis

                analysis = run_analysis(
                    image_bytes=concept_bytes,
                    media_type=media_type,
                    provider=provider,
                    product_context=product_context,
                )
                st.session_state.pkg_analysis = analysis
                st.session_state.pkg_enrichment = None  # reset enrichment
                st.rerun()
            except Exception as e:
                logger.exception("Analysis failed")
                st.error(f"B\u0142\u0105d analizy: {e}")
                return

    analysis: DesignAnalysis | None = st.session_state.pkg_analysis
    if not analysis:
        return

    # --- STEP 3: Display results ---
    st.markdown("---")
    st.subheader("Wyniki analizy")
    _render_analysis_results(analysis)

    # --- STEP 4: Enrichment ---
    st.markdown("---")
    st.subheader("Brakuj\u0105ce elementy")
    selected_ids, ean_number = _render_enrichment_ui(analysis)

    if selected_ids:
        if st.button("Generuj brakuj\u0105ce elementy", width="stretch"):
            from packaging_designer.pipeline import run_enrichment

            enrichment = run_enrichment(
                analysis=analysis,
                selected_ids=selected_ids,
                ean_number=ean_number,
            )
            st.session_state.pkg_enrichment = enrichment
            st.success(
                f"Wygenerowano {len(enrichment.generated_assets)} asset\u00f3w"
            )

    # --- STEP 4b: Back label (optional) ---
    st.markdown("---")
    generate_back = st.toggle("Generuj tyln\u0105 etykiet\u0119 (back label)", key="toggle_back")

    if generate_back:
        back_lang = st.selectbox(
            "J\u0119zyk tylnej etykiety",
            ["pl", "en", "de", "fr", "cs"],
            format_func=lambda c: {
                "pl": "Polski", "en": "English", "de": "Deutsch",
                "fr": "Fran\u00e7ais", "cs": "\u010ce\u0161tina",
            }.get(c, c),
            key="back_lang",
        )
        back_context = st.text_area(
            "Dodatkowe dane produktu (sk\u0142adniki, producent\u2026)",
            placeholder="Sk\u0142ad: mi\u0119so z kurczaka 40%, ry\u017c 20%...\nProducent: Firma X, ul. Y, Warszawa",
            key="back_context",
            height=100,
        )

        if st.button("Generuj back label", width="stretch"):
            with st.spinner("Generowanie tylnej etykiety\u2026"):
                try:
                    from packaging_designer.back_label import generate_back_label

                    provider = _get_provider()
                    back_content = generate_back_label(
                        analysis=analysis,
                        provider=provider,
                        language=back_lang,
                        user_context=back_context,
                    )
                    st.session_state.pkg_back_label = back_content
                    st.success(f"Wygenerowano {len(back_content.sections)} sekcji")
                except Exception as e:
                    logger.exception("Back label failed")
                    st.error(f"B\u0142\u0105d generowania: {e}")

        # Display back label content
        back_label = st.session_state.get("pkg_back_label")
        if back_label:
            with st.expander("Podgl\u0105d tylnej etykiety", expanded=True):
                for sec in back_label.sections:
                    if sec.title:
                        st.markdown(f"**{sec.title}**")
                    st.text(sec.content)
                    st.markdown("---")
                if back_label.feeding_table:
                    st.markdown("**Tabela dawkowania:**")
                    for row in back_label.feeding_table:
                        st.text(f"  {row.weight_range}  \u2192  {row.daily_amount}")

    # --- STEP 4c: Dieline preview ---
    st.markdown("---")
    show_dieline = st.toggle("Poka\u017c dieline (wykrojnik)", key="toggle_dieline")
    if show_dieline:
        from packaging_designer.generators.dieline import get_dieline_svg

        dieline_svg = get_dieline_svg(
            package_type=analysis.package_spec.package_type.value,
            width_mm=analysis.package_spec.dimensions.width_mm,
            height_mm=analysis.package_spec.dimensions.height_mm,
            depth_mm=analysis.package_spec.dimensions.depth_mm,
            bleed_mm=bleed_mm,
        )
        # st.image cannot render raw SVG — use HTML embed
        import base64 as _b64
        svg_b64 = _b64.b64encode(dieline_svg.encode()).decode()
        st.markdown(
            f'<img src="data:image/svg+xml;base64,{svg_b64}" '
            f'style="max-width:100%;background:white;padding:10px;border-radius:8px;" '
            f'alt="Dieline"/>',
            unsafe_allow_html=True,
        )
        st.caption("Dieline / wykrojnik")
        st.download_button(
            label="Pobierz dieline (.svg)",
            data=dieline_svg,
            file_name="dieline.svg",
            mime="image/svg+xml",
        )

    # --- STEP 4d: 3D mockup ---
    st.markdown("---")
    show_mockup = st.toggle("Poka\u017c 3D mockup", key="toggle_mockup")
    if show_mockup:
        from packaging_designer.builders.mockup_3d import generate_3d_mockup

        try:
            mockup_bytes = generate_3d_mockup(
                analysis=analysis,
                concept_image=concept_bytes,
            )
            st.image(mockup_bytes, caption="3D mockup")
        except Exception as e:
            st.warning(f"Mockup niedost\u0119pny: {e}")

    # --- STEP 5: Export ---
    st.markdown("---")
    st.subheader("Eksport DTP")
    try:
        _render_export(
            analysis=analysis,
            enrichment=st.session_state.pkg_enrichment,
            concept_bytes=concept_bytes,
            export_format=export_format,
            bleed_mm=bleed_mm,
        )
    except Exception as e:
        logger.exception("Export rendering failed")
        st.error(f"B\u0142\u0105d eksportu: {e}")


if __name__ == "__main__":
    main()
