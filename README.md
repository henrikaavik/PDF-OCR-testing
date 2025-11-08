# PDF OCR - Töötundide töötlemine

Streamlit-based prototype for extracting work-hour data from PDF files with OCR support.

## Features

- ✅ **Multi-file PDF processing** (up to 10 pages per file)
- 🔍 **Intelligent table extraction** (pdfplumber → camelot → OCR fallback)
- 🌍 **OCR support** for scanned documents (Estonian + English)
- 📊 **Quarterly aggregation** with pivot summaries
- 🤖 **AI provider benchmarking** (ChatGPT, Grok, Kimi, Gemini)
- 📈 **XLSX export** (per-file and aggregated reports)
- 🇪🇪 **Estonian language UI**

## Schema

The application extracts and normalizes data to the following schema:

- **Kuupäev** - Date in dd.mm.yyyy format (2000-2035)
- **Töötaja** - Employee name (text)
- **Projekt** - Project name (text)
- **Tunnid** - Hours worked (numeric, ≥ 0, rounded to 2 decimals)
- **Allikas** - Source filename (auto-added)

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

3. Install Tesseract OCR:

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr tesseract-ocr-est tesseract-ocr-eng
```

**macOS:**
```bash
brew install tesseract tesseract-lang
```

**Windows:**
Download installer from: https://github.com/UB-Mannheim/tesseract/wiki

4. Run the application:
```bash
streamlit run app.py
```

### Streamlit Cloud Deployment

1. Fork/push this repository to GitHub

2. Go to [share.streamlit.io](https://share.streamlit.io)

3. Create new app and select your repository

4. Add the following to your `packages.txt` file (create in root):
```
tesseract-ocr
tesseract-ocr-est
tesseract-ocr-eng
libgl1
```

5. Configure secrets (Settings → Secrets):
```toml
# Optional: Add API keys for AI providers
OPENAI_API_KEY = "sk-..."
GROK_API_KEY = "xai-..."
KIMI_API_KEY = "..."
GEMINI_API_KEY = "..."
```

6. Deploy!

## Usage

### 1. Upload PDFs

- Upload one or more PDF files (max 10 pages each)
- Files with >10 pages will be rejected with a polite error message

### 2. Select AI Provider (Optional)

Choose from:
- **Pole (ainult reeglid)** - Rule-based only, no AI
- **ChatGPT** - OpenAI GPT-4
- **Grok** - xAI Grok
- **Kimi** - Moonshot AI
- **Gemini** - Google Gemini

Enter API key or configure in `st.secrets`

### 3. Process Files

- Click "Töötle failid" to start processing
- View per-file results with:
  - Data preview
  - Validation warnings
  - Download individual XLSX reports

### 4. Generate Quarterly Report

- Switch to "Kvartaliaruanne" tab
- View pivot summary (Töötaja × Projekt × Month)
- Download aggregated XLSX with two sheets:
  - **Koond** - Pivot summary
  - **Toorandmed** - All raw data

### 5. Benchmark AI Providers

- Switch to "Võrdlus" tab
- Compare:
  - API call count
  - Total & average latency
  - Accuracy percentage

## Architecture

```
pdf-ocr-testing/
├── app.py                 # Main Streamlit application
├── core/
│   ├── ingest.py         # Page validation & classification
│   ├── ocr.py            # Pytesseract OCR (et+en)
│   ├── tables.py         # Table extraction (multi-method)
│   ├── normalize.py      # Schema mapping & normalization
│   ├── validate.py       # Rule-based validation
│   ├── aggregate.py      # Quarterly aggregation & pivot
│   └── providers/
│       ├── base.py       # AI provider interface
│       ├── openai_provider.py
│       ├── grok_provider.py
│       ├── kimi_provider.py
│       └── gemini_provider.py
├── utils/
│   ├── dates.py          # Date parsing & quarter logic
│   ├── io.py             # XLSX export
│   └── parallel.py       # Concurrent processing
└── requirements.txt
```

## Data Processing Pipeline

1. **Ingest**: Validate page count (≤10), classify pages as text/OCR
2. **Extract**: Try pdfplumber → camelot (lattice) → camelot (stream) → OCR fallback
3. **Normalize**: Map headers to schema, normalize date/number formats
4. **Validate**: Check date format, numeric ranges, required fields
5. **Aggregate**: Derive quarters, create pivot summaries
6. **Export**: Generate XLSX with proper formatting

## Validation Rules

- **Kuupäev**: Must match dd.mm.yyyy and be within 2000-2035
- **Tunnid**: Must be numeric, ≥ 0, rounded to 2 decimals (half-up)
- **Töötaja & Projekt**: Cannot be empty
- **Total consistency**: If document contains "Kokku/Total", verify sum matches (tolerance: 0.01)

## AI Provider Configuration

### OpenAI (ChatGPT)
```python
# In secrets.toml
OPENAI_API_KEY = "sk-..."
```

### Grok (xAI)
```python
# In secrets.toml
GROK_API_KEY = "xai-..."
```

### Kimi (Moonshot)
```python
# In secrets.toml
KIMI_API_KEY = "..."
```

### Gemini (Google)
```python
# In secrets.toml
GEMINI_API_KEY = "..."
```

## Testing

To test the application, use sample PDF files containing work-hour tables with:
- Various header formats (Estonian/English)
- Mixed text and scanned pages
- Different table layouts
- Total rows for consistency checking

Minimum 10 sample PDFs recommended for MVP validation.

## Troubleshooting

### Tesseract not found
```bash
# Check installation
tesseract --version

# Check language data
tesseract --list-langs
```

### Camelot errors
Camelot requires Ghostscript and OpenCV:
```bash
# Ubuntu
sudo apt-get install ghostscript

# macOS
brew install ghostscript
```

### API rate limits
Switch to "Pole (ainult reeglid)" mode to process without AI enhancement.

## Performance

- **Local**: Fast for text-based PDFs, slower for OCR
- **Streamlit Cloud**: Limited by free tier resources
- **Parallel processing**: Enabled for multi-file batches
- **AI calls**: Can be disabled for rule-based only processing

## License

MIT

## Contact

For questions or issues, please open a GitHub issue at:
https://github.com/henrikaavik/PDF-OCR-testing/issues
