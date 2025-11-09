"""
Streamlit PDF Table Extraction Application
Universal PDF to XLSX converter using AI Vision APIs
"""

import streamlit as st
import pandas as pd
from typing import List, Dict, Any
import io

# Version
__version__ = "3.1.2"  # Optimization: Reduced DPI to 300 (avoids Gemini downscaling)

# Core imports
from core.ingest import ingest_pdf, PageLimitExceededError
from core.ocr import pdf_to_images
from core.providers.base import create_provider

# Utils imports
from utils.io import create_per_file_xlsx


# Page configuration
st.set_page_config(
    page_title="PDF Table Extractor",
    page_icon="📊",
    layout="wide"
)


def process_single_pdf(filename: str, pdf_bytes: bytes, provider) -> Dict[str, Any]:
    """
    Process a single PDF file using AI Vision API.

    Args:
        filename: Original filename
        pdf_bytes: PDF file bytes
        provider: AI provider instance

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
        # Step 1: Ingest (page count check only)
        ingest_result = ingest_pdf(pdf_bytes, filename)

        # Step 2: Convert to images (optimal DPI: 300 avoids Gemini downscaling)
        images = pdf_to_images(pdf_bytes, dpi=300)

        # Step 3: Extract with Vision API
        all_data = []
        all_columns = []
        all_tables = []  # NEW: Collect separate tables
        tables_found = 0
        combined_formatting = {
            'merged_cells': [],
            'cell_borders': {},
            'header_rows': [],
            'total_rows': [],
            'bold_cells': []
        }

        for page_num, image in enumerate(images):
            # Convert PIL Image to bytes
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            image_bytes = img_byte_arr.getvalue()

            # Extract from image using Vision API
            result = provider.extract_table_from_image(
                image_bytes,
                context=f"{filename} page {page_num+1}"
            )

            if result['success']:
                # Collect rows (legacy)
                if result.get('rows'):
                    all_data.extend(result['rows'])

                # Collect columns (from first page - legacy)
                if not all_columns and result.get('columns'):
                    all_columns = result['columns']

                # Collect separate tables (NEW)
                if result.get('tables'):
                    all_tables.extend(result['tables'])

                # Track tables found
                metadata = result.get('metadata', {})
                if metadata.get('tables_found'):
                    tables_found += metadata['tables_found']

                # Merge formatting (legacy)
                page_formatting = result.get('formatting', {})
                if page_formatting:
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

        # Step 4: Calculate cost
        file_cost = 0.0
        file_tokens = 0
        if provider:
            metrics = provider.get_metrics()
            file_cost = metrics['total_cost_eur'] - cost_before
            file_tokens = metrics['total_tokens'] - tokens_before

        # Step 5: Return (NO VALIDATION)
        return {
            'filename': filename,
            'success': len(all_data) > 0,
            'page_count': ingest_result['page_count'],
            'tables_found': tables_found,
            'rows_extracted': len(all_data),
            'columns': all_columns,
            'data': all_data,
            'tables': all_tables,  # NEW: Separate tables
            'formatting': combined_formatting,
            'ai_cost': file_cost,
            'ai_tokens': file_tokens,
            'error': None if len(all_data) > 0 else 'No data extracted'
        }

    except PageLimitExceededError as e:
        return {
            'filename': filename,
            'success': False,
            'error': str(e),
            'data': [],
            'columns': [],
            'tables': [],
            'formatting': {}
        }

    except Exception as e:
        return {
            'filename': filename,
            'success': False,
            'error': str(e),
            'data': [],
            'columns': [],
            'tables': [],
            'formatting': {}
        }


def main():
    """Main Streamlit application."""

    st.title("📊 PDF Tabeli Konverter")
    st.markdown(f"*Ekstraheeri tabeleid PDF-idest ja ekspordi XLSX-iks* • `v{__version__}`")

    # Sidebar for settings
    with st.sidebar:
        st.header("⚙️ Seaded")

        # AI Provider selection
        st.subheader("AI teenusepakkuja")
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
            help="AI Vision API ekstraheerib tabeleid PDF-ist"
        )

        provider_type = provider_options[selected_provider_name]

        # API Key input
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
            "**Meetod:** AI Vision API\n\n"
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

    # Main content (single tab)
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

            # Display results
            st.success(f"✅ Töödeldud {len(results)} faili")

            # Show AI cost summary
            if provider:
                metrics = provider.get_metrics()
                if metrics['total_tokens'] > 0:
                    st.info(f"💰 **AI kulu kokku:** €{metrics['total_cost_eur']:.4f} | 🎯 **Tokenit:** {metrics['total_tokens']:,}")

            # Show per-file results
            for result in results:
                with st.expander(f"📄 {result['filename']}", expanded=True):
                    if result['success']:
                        col1, col2, col3 = st.columns(3)
                        col1.metric("Lehekülgi", result.get('page_count', 0))
                        col2.metric("Ridu ekstraheeritud", result.get('rows_extracted', 0))
                        col3.metric("Tabeleid leitud", result.get('tables_found', 0))

                        # Show AI cost per file
                        ai_tokens = result.get('ai_tokens', 0)
                        ai_cost = result.get('ai_cost', 0.0)
                        if ai_tokens > 0:
                            st.caption(f"💰 AI kulu: €{ai_cost:.4f} | 🎯 Tokenit: {ai_tokens:,}")

                        # Data preview
                        if result.get('data'):
                            st.subheader("Andmete eelvaade")
                            df = pd.DataFrame(result['data'])
                            st.dataframe(df, use_container_width=True)

                            # Download per-file XLSX
                            xlsx_bytes = create_per_file_xlsx(
                                result['data'],
                                result['filename'],
                                result.get('columns'),
                                result.get('formatting'),
                                result.get('tables')  # NEW: Pass separate tables
                            )
                            st.download_button(
                                label="⬇️ Laadi alla XLSX",
                                data=xlsx_bytes,
                                file_name=f"{result['filename']}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                    else:
                        st.error(f"❌ {result.get('error', 'Tundmatu viga')}")


if __name__ == "__main__":
    main()
