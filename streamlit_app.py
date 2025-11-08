"""
Streamlit PDF OCR Application
Eesti keeles (Estonian language UI)
"""

import streamlit as st
import pandas as pd
from typing import List, Dict, Any
import io

# Version
__version__ = "1.5.0"  # Improved multi-table detection and validation

# Core imports
from core.ingest import ingest_pdf, PageLimitExceededError
from core.ocr import ocr_pdf_page, ocr_pdf_all_pages, pdf_to_images
from core.tables import extract_all_tables, merge_tables, parse_table_from_text
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
    cost_before = 0.0
    tokens_before = 0

    if provider:
        metrics = provider.get_metrics()
        cost_before = metrics['total_cost_eur']
        tokens_before = metrics['total_tokens']

    try:
        # Step 1: Ingest and validate page count
        ingest_result = ingest_pdf(pdf_bytes, filename)

        # Step 2: Extract tables from all pages (rule-based)
        all_tables = extract_all_tables(pdf_bytes, ingest_result['pages'])

        all_vision_data = []
        all_columns = []
        vision_warnings = []
        vision_tables_count = 0
        used_vision_api = False

        # Step 3: If no tables found, use VISION API (PREMIUM METHOD)
        if not all_tables and provider and provider.name != "Pole (ainult reeglid)":
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

                if vision_result['success'] and vision_result['rows']:
                    used_vision_api = True
                    all_vision_data.extend(vision_result['rows'])

                    # Collect columns (from first successful extraction)
                    if not all_columns and vision_result.get('columns'):
                        all_columns = vision_result['columns']

                    # Collect metadata warnings
                    metadata = vision_result.get('metadata', {})

                    # Track number of tables found
                    if metadata.get('tables_found'):
                        vision_tables_count += metadata['tables_found']
                        vision_warnings.append(
                            f"Lehekülg {page_num+1}: Leitud {metadata['tables_found']} tabelit"
                        )

                    if metadata.get('calculated_fields'):
                        vision_warnings.append(
                            f"Lehekülg {page_num+1}: Arvutatud väljad: {', '.join(metadata['calculated_fields'])}"
                        )
                    if metadata.get('unreadable_fields'):
                        vision_warnings.append(
                            f"Lehekülg {page_num+1}: Loetamatud väljad: {', '.join(metadata['unreadable_fields'])}"
                        )

        # Step 4: Fallback to OCR + text parsing if vision failed
        if not all_tables and not all_vision_data:
            ocr_results = ocr_pdf_all_pages(pdf_bytes)

            for page_num, ocr_text in ocr_results:
                # Try rule-based text parsing
                parsed_table = parse_table_from_text(ocr_text)
                if parsed_table is not None:
                    all_tables.append(parsed_table)

        # Step 5: Merge tables or use vision data
        if all_vision_data:
            # Vision API gave us complete table structure
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

            # Add table structure info
            table_columns = all_columns
            table_data = validation_result['valid_data']  # Use validated data

        else:
            # Traditional pipeline: merge tables → normalize
            merged_table = merge_tables(all_tables) if all_tables else pd.DataFrame()

            # AI-enhanced normalization if available
            if provider and provider.name != "Pole (ainult reeglid)" and not merged_table.empty:
                merged_table = provider.normalize_table(merged_table, context=f"Work hours from {filename}")

            normalized_data = normalize_dataframe(merged_table)

            # Find expected total (if present)
            expected_total = find_total_row(merged_table) if not merged_table.empty else None

            # Validate
            validation_result = validate_file_data(normalized_data, expected_total)

            # For traditional path, columns are standard fields
            table_columns = ['Kuupäev', 'Töötaja', 'Projekt', 'Tunnid']
            table_data = validation_result['valid_data']

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
            'tables_found': vision_tables_count if used_vision_api else len(all_tables),
            'used_vision_api': used_vision_api,
            'columns': table_columns,
            'data': table_data,
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
            'warnings': [str(e)]
        }

    except Exception as e:
        return {
            'filename': filename,
            'success': False,
            'error': str(e),
            'data': [],
            'columns': [],
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

                # Show AI cost summary if provider was used
                if provider and provider.name != "Pole (ainult reeglid)":
                    metrics = provider.get_metrics()
                    if metrics['total_tokens'] > 0:
                        st.info(f"💰 **AI kulu kokku:** €{metrics['total_cost_eur']:.4f} | 🎯 **Tokenit:** {metrics['total_tokens']:,}")
                    else:
                        st.warning("⚠️ AI teenusepakkuja valitud, aga API päringuid ei tehtud. Kontrolli API võtit või kas failidest leiti tabeleid.")


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

                            # Show AI cost per file if available
                            if provider and provider.name != "Pole (ainult reeglid)":
                                ai_tokens = result.get('ai_tokens', 0)
                                ai_cost = result.get('ai_cost', 0.0)
                                if ai_tokens > 0:
                                    st.caption(f"💰 AI kulu: €{ai_cost:.4f} | 🎯 Tokenit: {ai_tokens:,}")
                                else:
                                    st.caption(f"⚠️ AI-d ei kasutatud (tabeleid ei leitud või viga)")

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
                                    result.get('columns')  # Pass columns if available
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
