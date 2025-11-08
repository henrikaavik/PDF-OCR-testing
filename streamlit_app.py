"""
Streamlit PDF OCR Application
Eesti keeles (Estonian language UI)
"""

import streamlit as st
import pandas as pd
from typing import List, Dict, Any
import io

# Version
__version__ = "2.1.0"  # Visual table structure extraction (borders, merged cells, bold text)

# Core imports
from core.ingest import ingest_pdf, PageLimitExceededError
from core.ocr import pdf_to_images
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
    Process a single PDF file using AI Vision API only.

    Args:
        filename: Original filename
        pdf_bytes: PDF file bytes
        provider: AI provider (required)

    Returns:
        Processing result dictionary
    """
    cost_before = 0.0
    tokens_before = 0

    if provider:
        metrics = provider.get_metrics()
        cost_before = metrics['total_cost_eur']
        tokens_before = metrics['total_tokens']

    try:
        # Step 1: Ingest and validate page count
        ingest_result = ingest_pdf(pdf_bytes, filename)

        # Step 2: Check if AI provider is available
        if not provider or provider.name == "Pole (ainult reeglid)":
            return {
                'filename': filename,
                'success': False,
                'error': 'AI teenusepakkuja on nõutav. Palun vali AI teenusepakkuja (ChatGPT, Grok, Kimi või Gemini).',
                'data': [],
                'columns': [],
                'formatting': {},
                'warnings': ['AI teenusepakkuja puudub. Rule-based meetodid on eemaldatud.']
            }

        # Step 3: Use VISION API to extract tables
        import json as debug_json

        all_vision_data = []
        all_columns = []
        vision_warnings = []
        vision_tables_count = 0
        combined_formatting = {
            'merged_cells': [],
            'cell_borders': {},
            'header_rows': [],
            'total_rows': [],
            'bold_cells': []
        }

        # Convert PDF pages to images
        images = pdf_to_images(pdf_bytes)

        for page_num, image in enumerate(images):
            # Convert PIL Image to bytes
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            image_bytes = img_byte_arr.getvalue()

            # Extract from image using Vision API
            vision_result = provider.extract_table_from_image(
                image_bytes,
                context=f"{filename} page {page_num+1}"
            )

            # DEBUG: Always log what Vision API returned
            vision_result_debug = {
                'success': vision_result.get('success'),
                'rows_count': len(vision_result.get('rows', [])),
                'columns_count': len(vision_result.get('columns', [])),
                'columns': vision_result.get('columns', []),
                'rows_sample': vision_result.get('rows', [])[:3] if vision_result.get('rows') else [],
                'metadata': vision_result.get('metadata', {})
            }
            vision_warnings.append(
                f"DEBUG - Lehekülg {page_num+1}:\n```json\n{debug_json.dumps(vision_result_debug, indent=2, ensure_ascii=False)}\n```"
            )

            if vision_result['success']:
                # Collect metadata ALWAYS (even if no rows extracted)
                metadata = vision_result.get('metadata', {})

                # Track number of tables found
                if metadata.get('tables_found'):
                    vision_tables_count += metadata['tables_found']
                    vision_warnings.append(
                        f"Lehekülg {page_num+1}: Leitud {metadata['tables_found']} tabelit"
                    )

                # Collect formatting metadata from this page
                page_formatting = vision_result.get('formatting', {})
                if page_formatting:
                    # Merge formatting from this page into combined formatting
                    if page_formatting.get('merged_cells'):
                        combined_formatting['merged_cells'].extend(page_formatting['merged_cells'])
                    if page_formatting.get('cell_borders'):
                        combined_formatting['cell_borders'].update(page_formatting['cell_borders'])
                    if page_formatting.get('header_rows'):
                        combined_formatting['header_rows'].extend(page_formatting['header_rows'])
                    if page_formatting.get('total_rows'):
                        combined_formatting['total_rows'].extend(page_formatting['total_rows'])
                    if page_formatting.get('bold_cells'):
                        combined_formatting['bold_cells'].extend(page_formatting['bold_cells'])

                    vision_warnings.append(
                        f"Lehekülg {page_num+1}: Leitud vormindus - "
                        f"Ühendatud lahtrid: {len(page_formatting.get('merged_cells', []))}, "
                        f"Piirjooned: {len(page_formatting.get('cell_borders', {}))}, "
                        f"Paksud lahtrid: {len(page_formatting.get('bold_cells', []))}"
                    )

                # Only process rows if they exist
                if vision_result.get('rows'):
                    all_vision_data.extend(vision_result['rows'])

                    # Collect columns (from first successful extraction)
                    if not all_columns and vision_result.get('columns'):
                        all_columns = vision_result['columns']

                    # Additional metadata warnings
                    if metadata.get('calculated_fields'):
                        vision_warnings.append(
                            f"Lehekülg {page_num+1}: Arvutatud väljad: {', '.join(metadata['calculated_fields'])}"
                        )
                    if metadata.get('unreadable_fields'):
                        vision_warnings.append(
                            f"Lehekülg {page_num+1}: Loetamatud väljad: {', '.join(metadata['unreadable_fields'])}"
                        )

                    vision_warnings.append(
                        f"Lehekülg {page_num+1}: Ekstraheeritud {len(vision_result['rows'])} rida"
                    )
                else:
                    # Warn if tables found but no rows extracted
                    if metadata.get('tables_found', 0) > 0:
                        vision_warnings.append(
                            f"⚠️ Lehekülg {page_num+1}: Leitud {metadata['tables_found']} tabelit, "
                            f"aga ühtegi rida ei ekstraheeritud! AI ei suutnud tabeleid lugeda."
                        )
            else:
                # Vision API failed
                error_msg = vision_result.get('metadata', {}).get('error', 'Tundmatu viga')
                vision_warnings.append(
                    f"❌ Lehekülg {page_num+1}: Vision API ebaõnnestus - {error_msg}"
                )

        # Step 4: Process extracted data
        if not all_vision_data:
            # No data extracted
            return {
                'filename': filename,
                'success': False,
                'error': 'Vision API ei suutnud ühtegi rida ekstraheerida.',
                'data': [],
                'columns': all_columns,
                'formatting': combined_formatting,
                'warnings': vision_warnings,
                'page_count': ingest_result['page_count'],
                'tables_found': vision_tables_count,
                'used_vision_api': True,
                'total_hours': 0.0,
                'valid_row_count': 0,
                'invalid_row_count': 0,
                'ai_cost': 0.0,
                'ai_tokens': 0
            }

        # Check if standard fields exist for validation
        has_standard_fields = all_columns and all(
            field in all_columns for field in ['Kuupäev', 'Töötaja', 'Projekt', 'Tunnid']
        )

        if has_standard_fields:
            # We have standard fields, can validate
            validation_result = validate_file_data(all_vision_data, None)
            if vision_warnings:
                validation_result['warnings'].extend(vision_warnings)

            # If validation rejected all rows, show everything anyway (Vision API mode)
            if not validation_result['valid_data'] and all_vision_data:
                validation_result['warnings'].append(
                    f"⚠️ Standardväljad leitud, aga valideerimise käigus kõik read tagasi lükatud. "
                    f"Näitan kõiki andmeid ilma valideerimiseta."
                )
                validation_result = {
                    'valid_data': all_vision_data,
                    'warnings': validation_result['warnings'],
                    'total_hours': 0.0,
                    'valid_row_count': len(all_vision_data),
                    'invalid_row_count': 0
                }
        else:
            # No standard fields, skip validation
            validation_result = {
                'valid_data': all_vision_data,
                'warnings': vision_warnings.copy() if vision_warnings else [],
                'total_hours': 0.0,
                'valid_row_count': len(all_vision_data),
                'invalid_row_count': 0
            }

        # Calculate cost for this file
        file_cost = 0.0
        file_tokens = 0
        if provider:
            metrics = provider.get_metrics()
            file_cost = metrics['total_cost_eur'] - cost_before
            file_tokens = metrics['total_tokens'] - tokens_before

        return {
            'filename': filename,
            'success': True,
            'page_count': ingest_result['page_count'],
            'tables_found': vision_tables_count,
            'used_vision_api': True,
            'columns': all_columns,
            'data': validation_result['valid_data'],
            'formatting': combined_formatting,
            'warnings': validation_result['warnings'],
            'total_hours': validation_result['total_hours'],
            'valid_row_count': validation_result['valid_row_count'],
            'invalid_row_count': validation_result['invalid_row_count'],
            'ai_cost': file_cost,
            'ai_tokens': file_tokens
        }

    except PageLimitExceededError as e:
        return {
            'filename': filename,
            'success': False,
            'error': str(e),
            'data': [],
            'columns': [],
            'formatting': {},
            'warnings': [str(e)]
        }

    except Exception as e:
        return {
            'filename': filename,
            'success': False,
            'error': str(e),
            'data': [],
            'columns': [],
            'formatting': {},
            'warnings': [f"Viga faili töötlemisel: {str(e)}"]
        }


def main():
    """Main Streamlit application."""

    st.title("📄 PDF OCR - Töötundide töötlemine")
    st.markdown(f"*Tööajaandmete ekstraheerimine PDF-failidest* • `v{__version__}`")

    # Sidebar for settings
    with st.sidebar:
        st.header("⚙️ Seaded")

        # AI Provider selection
        st.subheader("AI teenusepakkuja (NÕUTAV)")
        provider_options = {
            "Gemini (Google)": "gemini",
            "ChatGPT (OpenAI)": "openai",
            "Grok (xAI)": "grok",
            "Kimi (Moonshot)": "kimi"
        }

        selected_provider_name = st.selectbox(
            "Vali teenusepakkuja:",
            options=list(provider_options.keys()),
            index=0,
            help="AI Vision API on nõutav PDF-ide töötlemiseks. Rule-based meetodid on eemaldatud."
        )

        provider_type = provider_options[selected_provider_name]

        # API Key input (always required)
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
            "**Meetod:** AI Vision API ainult\n\n"
            "**Maksimaalne lehekülgede arv:** 10\n\n"
            "**Toetatud vormingud:** PDF\n\n"
            "**Väljund:** XLSX (Excel)"
        )

        st.divider()

        # Reload button
        st.subheader("🔄 Uuenda")
        if st.button("🔄 Laadi rakendus uuesti", use_container_width=True):
            # Clear all caches
            st.cache_data.clear()
            st.cache_resource.clear()
            # Clear session state
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            # Rerun the app
            st.rerun()

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
                # Create provider (always required)
                provider = None
                if not api_key:
                    st.error("❌ AI API võti on nõutav! Palun sisesta API võti külgpaneelil.")
                else:
                    try:
                        provider = create_provider(provider_type, api_key)
                    except Exception as e:
                        st.error(f"Viga teenusepakkuja loomisel: {str(e)}")

                if not provider:
                    st.stop()

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

                # Show AI cost summary
                if provider:
                    metrics = provider.get_metrics()
                    if metrics['total_tokens'] > 0:
                        st.info(f"💰 **AI kulu kokku:** €{metrics['total_cost_eur']:.4f} | 🎯 **Tokenit:** {metrics['total_tokens']:,}")
                    else:
                        st.warning("⚠️ API päringuid ei tehtud. Kontrolli API võtit.")


                # Show per-file results
                for result in results:
                    with st.expander(f"📄 {result['filename']}", expanded=True):
                        if result['success']:
                            col1, col2, col3 = st.columns(3)
                            col1.metric("Lehekülgi", result.get('page_count', 0))
                            col2.metric("Kehtivaid ridu", result.get('valid_row_count', 0))
                            col3.metric("Tunde kokku", f"{result.get('total_hours', 0):.2f}")

                            # Show tables found
                            st.caption(f"📊 Tabeleid leitud: {result.get('tables_found', 0)}")

                            # Show AI cost per file
                            ai_tokens = result.get('ai_tokens', 0)
                            ai_cost = result.get('ai_cost', 0.0)
                            if ai_tokens > 0:
                                st.caption(f"💰 AI kulu: €{ai_cost:.4f} | 🎯 Tokenit: {ai_tokens:,}")
                            else:
                                st.caption(f"⚠️ AI-d ei kasutatud (viga)")

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
                                    result['filename'],
                                    result.get('columns'),  # Pass columns if available
                                    result.get('formatting')  # Pass formatting if available
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

            # Performance metrics
            col1, col2, col3 = st.columns(3)
            col1.metric("API päringud", metrics['calls'])
            col2.metric("Kogu latentsus (s)", f"{metrics['total_latency']:.3f}")
            col3.metric("Keskmine latentsus (s)", f"{metrics['avg_latency']:.3f}")

            # Cost metrics
            st.divider()
            st.subheader("💰 Kulud")
            col1, col2, col3 = st.columns(3)
            col1.metric("🎯 Tokenit kokku", f"{metrics['total_tokens']:,}")
            col2.metric("💰 Kulu (EUR)", f"€{metrics['total_cost_eur']:.4f}")

            # Calculate accuracy
            if 'results' in st.session_state:
                total_rows = sum(r.get('valid_row_count', 0) + r.get('invalid_row_count', 0)
                               for r in st.session_state['results'])
                valid_rows = sum(r.get('valid_row_count', 0)
                               for r in st.session_state['results'])

                accuracy = (valid_rows / total_rows * 100) if total_rows > 0 else 0

                col3.metric("Täpsus", f"{accuracy:.1f}%")

                # Cost efficiency
                if metrics['total_cost_eur'] > 0 and valid_rows > 0:
                    cost_per_row = metrics['total_cost_eur'] / valid_rows
                    st.caption(f"📊 Keskmine kulu rea kohta: €{cost_per_row:.6f}")
        else:
            st.info("AI teenusepakkuja ei ole valitud või kasutuses.")


if __name__ == "__main__":
    main()
