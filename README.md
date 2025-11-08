# PDF Table Extractor

Universal PDF to XLSX converter using AI Vision APIs. Extract tables from any PDF document and export to Excel with formatting preservation.

## Features

- ✅ **Multi-file PDF processing** (up to 10 pages per file)
- 🤖 **AI Vision API extraction** (Gemini, OpenAI GPT-4o, Grok, Kimi)
- 🎨 **Visual structure preservation** (borders, merged cells, bold text)
- 📊 **XLSX export with formatting**
- 💰 **Cost tracking** (token usage and EUR cost per file)
- 🌍 **No validation** - exports exactly what Vision API returns

## How It Works

1. **Upload PDFs** - Select one or more PDF files (max 10 pages each)
2. **AI Extraction** - Vision API analyzes each page and extracts table data
3. **Formatting Detection** - Preserves visual structure (merged cells, borders, bold)
4. **XLSX Export** - Download Excel files with original formatting

## Installation

### Local Development

1. Clone the repository:
```bash
git clone https://github.com/henrikaavik/PDF-OCR-testing.git
cd PDF-OCR-testing
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
streamlit run streamlit_app.py
```

### Streamlit Cloud Deployment

1. Fork/push this repository to GitHub

2. Go to [share.streamlit.io](https://share.streamlit.io)

3. Create new app and select your repository

4. Configure secrets (Settings → Secrets):
```toml
# Add API keys for AI providers
OPENAI_API_KEY = "sk-..."
GROK_API_KEY = "xai-..."
KIMI_API_KEY = "..."
GEMINI_API_KEY = "..."
```

5. Deploy!

## Usage

### 1. Select AI Provider

Choose from:
- **Gemini** - Google Gemini 1.5 Pro (best for vision)
- **ChatGPT** - OpenAI GPT-4o
- **Grok** - xAI Grok (OpenAI-compatible)
- **Kimi** - Moonshot AI (OpenAI-compatible)

Enter API key or configure in `st.secrets`

### 2. Upload PDFs

- Upload one or more PDF files (max 10 pages each)
- Files with >10 pages will be rejected (cost protection)

### 3. Process Files

- Click "Töötle failid" to start processing
- View per-file results with:
  - Page count
  - Rows extracted
  - Tables found
  - AI cost (tokens + EUR)
  - Data preview
  - Download individual XLSX reports

## Architecture

```
t88lehed-tabelina/
├── streamlit_app.py           # Main Streamlit application
├── core/
│   ├── ingest.py              # Page validation & limit checks
│   ├── ocr.py                 # PDF to image conversion
│   └── providers/
│       ├── base.py            # AI provider interface
│       ├── gemini_provider.py # Google Gemini
│       ├── openai_provider.py # OpenAI GPT-4o
│       ├── grok_provider.py   # xAI Grok
│       └── kimi_provider.py   # Moonshot AI Kimi
├── utils/
│   └── io.py                  # XLSX export with formatting
└── requirements.txt
```

## Data Processing Pipeline

1. **Ingest**: Validate page count (≤10)
2. **Convert**: PDF pages to images
3. **Extract**: Vision API analyzes images and returns:
   - Column names
   - Row data (as dictionaries)
   - Table metadata (count, confidence)
   - Formatting (merged cells, borders, bold)
4. **Export**: Generate XLSX with visual formatting preserved

## AI Provider Pricing

All costs shown in EUR:

| Provider | Input (1M tokens) | Output (1M tokens) |
|----------|-------------------|-------------------|
| Gemini 1.5 Pro | €1.21 | €4.40 |
| GPT-4o | €4.40 | €13.20 |
| Grok | €4.40 | €13.20 |
| Kimi | €1.56 | €1.56 |

## Formatting Preservation

The Vision API detects and exports:

- **Merged cells** - Cells spanning multiple columns/rows
- **Cell borders** - Individual border visibility (top, bottom, left, right)
- **Header rows** - Rows containing table headers
- **Total rows** - Rows containing sums/totals
- **Bold cells** - Emphasized text cells

All formatting is preserved in the exported XLSX file.

## Performance

- **Page limit**: 10 pages per PDF (cost protection)
- **Batch processing**: Processes multiple files sequentially
- **Cost tracking**: Real-time token usage and EUR cost per file
- **No validation**: Exports exactly what Vision API returns (no data modification)

## Version History

- **v3.0.0** - Universal PDF table extractor (removed validation, quarterly reports)
- **v2.1.2** - Bug fix: Show warnings even when processing fails
- **v2.1.0** - Added Vision API formatting preservation
- **v2.0.0** - Added AI Vision API support
- **v1.0.0** - Initial release with rule-based extraction

## License

MIT

## Contact

For questions or issues, please open a GitHub issue at:
https://github.com/henrikaavik/PDF-OCR-testing/issues
