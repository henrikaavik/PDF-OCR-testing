"""
Streamlit PDF OCR Application
Eesti keeles (Estonian language UI)
"""

import streamlit as st
import pandas as pd
from typing import List, Dict, Any
import io

# Core imports
from core.ingest import ingest_pdf, PageLimitExceededError
from core.ocr import ocr_pdf_page, ocr_pdf_all_pages
from core.tables import extract_all_tables, merge_tables
from core.normalize import normalize_dataframe, find_total_row
from core.validate import validate_file_data
from core.aggregate import aggregate_multiple_files, get_quarter_summary_text
from core.providers.base import create_provider

# Utils imports
from utils.io import create_per_file_xlsx, create_quarterly_xlsx
from utils.parallel import process_files_parallel


# Page configuration
st.set_page_config(
    page_title="PDF OCR - Töötundide töötlemine",
    page_icon="📄",
    layout="wide"
)


def process_single_pdf(filename: str, pdf_bytes: bytes, provider=None) -> Dict[str, Any]:
    """
    Process a single PDF file through the entire pipeline.

    Args:
        filename: Original filename
        pdf_bytes: PDF file bytes
        provider: Optional AI provider for enhancement

    Returns:
        Processing result dictionary
    """
    try:
        # Step 1: Ingest and validate page count
        ingest_result = ingest_pdf(pdf_bytes, filename)

        # Step 2: Extract tables from all pages
        all_tables = extract_all_tables(pdf_bytes, ingest_result['pages'])

        # If no tables found, try OCR on all pages
        if not all_tables:
            ocr_results = ocr_pdf_all_pages(pdf_bytes)
            # Could add AI enhancement here if provider is available
            # For now, just note that OCR was performed

        # Step 3: Merge tables
        merged_table = merge_tables(all_tables) if all_tables else pd.DataFrame()

        # Step 4: Normalize data
        normalized_data = normalize_dataframe(merged_table)

        # Step 5: Find expected total (if present)
        expected_total = find_total_row(merged_table) if not merged_table.empty else None

        # Step 6: Validate
        validation_result = validate_file_data(normalized_data, expected_total)

        return {
            'filename': filename,
            'success': True,
            'page_count': ingest_result['page_count'],
            'tables_found': len(all_tables),
            'data': validation_result['valid_data'],
            'warnings': validation_result['warnings'],
            'total_hours': validation_result['total_hours'],
            'valid_row_count': validation_result['valid_row_count'],
            'invalid_row_count': validation_result['invalid_row_count']
        }

    except PageLimitExceededError as e:
        return {
            'filename': filename,
            'success': False,
            'error': str(e),
            'data': [],
            'warnings': [str(e)]
        }

    except Exception as e:
        return {
            'filename': filename,
            'success': False,
            'error': str(e),
            'data': [],
            'warnings': [f"Viga faili töötlemisel: {str(e)}"]
        }


def main():
    """Main Streamlit application."""

    st.title("📄 PDF OCR - Töötundide töötlemine")
    st.markdown("*Tööajaandmete ekstraheerimine PDF-failidest*")

    # Sidebar for settings
    with st.sidebar:
        st.header("⚙️ Seaded")

        # AI Provider selection
        st.subheader("AI teenusepakkuja")
        provider_options = {
            "Pole (ainult reeglid)": "none",
            "ChatGPT (OpenAI)": "openai",
            "Grok (xAI)": "grok",
            "Kimi (Moonshot)": "kimi",
            "Gemini (Google)": "gemini"
        }

        selected_provider_name = st.selectbox(
            "Vali teenusepakkuja:",
            options=list(provider_options.keys()),
            index=0
        )

        provider_type = provider_options[selected_provider_name]

        # API Key input (if needed)
        api_key = None
        if provider_type != "none":
            api_key = st.text_input(
                f"API võti ({selected_provider_name}):",
                type="password",
                help="API võti salvestatakse st.secrets failis tootmisversioonis"
            )

            # Try to get from secrets if not provided
            if not api_key:
                secret_key = f"{provider_type}_api_key".upper()
                api_key = st.secrets.get(secret_key, None)

        st.divider()

        st.subheader("ℹ️ Info")
        st.info(
            "**Maksimaalne lehekülgede arv:** 10\n\n"
            "**Toetatud vormingud:** PDF\n\n"
            "**Väljund:** XLSX (Excel)"
        )

    # Main content
    tab1, tab2, tab3 = st.tabs(["📤 Lae üles", "📊 Kvartaliaruanne", "🔍 Võrdlus"])

    with tab1:
        st.header("Laadi üles PDF-failid")

        uploaded_files = st.file_uploader(
            "Vali üks või mitu PDF-faili (maksimaalselt 10 lehekülge faili kohta):",
            type=['pdf'],
            accept_multiple_files=True
        )

        if uploaded_files:
            st.info(f"Laaditud failid: {len(uploaded_files)}")

            if st.button("🚀 Töötle failid", type="primary"):
                # Create provider
                provider = None
                if provider_type != "none" and api_key:
                    try:
                        provider = create_provider(provider_type, api_key)
                    except Exception as e:
                        st.error(f"Viga teenusepakkuja loomisel: {str(e)}")

                # Prepare files for processing
                files_to_process = [
                    (file.name, file.getvalue())
                    for file in uploaded_files
                ]

                # Process files
                with st.spinner("Töötlen faile..."):
                    results = []
                    for filename, file_bytes in files_to_process:
                        result = process_single_pdf(filename, file_bytes, provider)
                        results.append(result)

                # Store results in session state
                st.session_state['results'] = results
                st.session_state['provider'] = provider

                # Display results
                st.success(f"✅ Töödeldud {len(results)} faili")

                # Show per-file results
                for result in results:
                    with st.expander(f"📄 {result['filename']}", expanded=True):
                        if result['success']:
                            col1, col2, col3 = st.columns(3)
                            col1.metric("Lehekülgi", result.get('page_count', 0))
                            col2.metric("Kehtivaid ridu", result.get('valid_row_count', 0))
                            col3.metric("Tunde kokku", f"{result.get('total_hours', 0):.2f}")

                            # Warnings
                            if result.get('warnings'):
                                st.warning("⚠️ Hoiatused:")
                                for warning in result['warnings']:
                                    st.write(f"- {warning}")

                            # Data preview
                            if result.get('data'):
                                st.subheader("Andmete eelvaade")
                                df = pd.DataFrame(result['data'])
                                st.dataframe(df, use_container_width=True)

                                # Download per-file XLSX
                                xlsx_bytes = create_per_file_xlsx(
                                    result['data'],
                                    result['filename']
                                )
                                st.download_button(
                                    label="⬇️ Laadi alla XLSX",
                                    data=xlsx_bytes,
                                    file_name=f"{result['filename']}.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                )
                        else:
                            st.error(f"❌ {result.get('error', 'Tundmatu viga')}")

    with tab2:
        st.header("Kvartaliaruanne")

        if 'results' in st.session_state:
            results = st.session_state['results']

            # Aggregate
            aggregated = aggregate_multiple_files(results)

            if aggregated['total_rows'] > 0:
                # Summary
                st.subheader("Kokkuvõte")
                summary_text = get_quarter_summary_text(
                    aggregated['quarters'],
                    aggregated['total_hours'],
                    aggregated['total_rows']
                )
                st.info(summary_text)

                # Pivot table
                st.subheader("Koondtabel (Töötaja × Projekt × Kuu)")
                st.dataframe(aggregated['pivot'], use_container_width=True)

                # Download quarterly report
                quarterly_xlsx = create_quarterly_xlsx(
                    aggregated['all_data'],
                    aggregated['pivot']
                )

                st.download_button(
                    label="⬇️ Laadi alla kvartaliaruanne (XLSX)",
                    data=quarterly_xlsx,
                    file_name="kvartaliaruanne.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary"
                )
            else:
                st.warning("Andmed puuduvad. Palun töötle esmalt faile.")
        else:
            st.info("Andmed puuduvad. Palun töötle esmalt faile vahekaardil 'Lae üles'.")

    with tab3:
        st.header("AI teenusepakkujate võrdlus")

        if 'provider' in st.session_state and st.session_state['provider']:
            provider = st.session_state['provider']

            # Get metrics
            metrics = provider.get_metrics()

            st.subheader(f"Teenusepakkuja: {metrics['name']}")

            col1, col2, col3 = st.columns(3)
            col1.metric("API päringud", metrics['calls'])
            col2.metric("Kogu latentsus (s)", f"{metrics['total_latency']:.3f}")
            col3.metric("Keskmine latentsus (s)", f"{metrics['avg_latency']:.3f}")

            # Calculate accuracy
            if 'results' in st.session_state:
                total_rows = sum(r.get('valid_row_count', 0) + r.get('invalid_row_count', 0)
                               for r in st.session_state['results'])
                valid_rows = sum(r.get('valid_row_count', 0)
                               for r in st.session_state['results'])

                accuracy = (valid_rows / total_rows * 100) if total_rows > 0 else 0

                st.metric("Täpsus", f"{accuracy:.1f}%")
        else:
            st.info("AI teenusepakkuja ei ole valitud või kasutuses.")


if __name__ == "__main__":
    main()
