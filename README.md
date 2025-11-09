# PDF Table Extractor

Universal PDF to XLSX converter using AI Vision APIs. Extract tables from any PDF document and export to Excel with formatting preservation.

## Features

- ✅ **Multi-file PDF processing** (up to 10 pages per file)
- 🤖 **AI Vision API extraction** (Gemini, OpenAI GPT-4o, Grok, Kimi)
- 🎯 **Structured Outputs** (OpenAI: 100% schema adherence guaranteed)
- 🔧 **Custom prompt editor** (tune extraction prompts in real-time)
- 🎨 **Visual structure preservation** (borders, merged cells, bold text)
- 📊 **XLSX export with formatting**
- 💰 **Cost tracking** (token usage and EUR cost per file)
- 🌍 **No validation** - exports exactly what Vision API returns

## How It Works

1. **Upload PDFs** - Select one or more PDF files (max 10 pages each)
2. **Configure Prompt** (optional) - Edit Vision API prompt to improve extraction
3. **AI Extraction** - Vision API analyzes each page and extracts table data
4. **Formatting Detection** - Preserves visual structure (merged cells, borders, bold)
5. **XLSX Export** - Download Excel files with original formatting

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
- **Gemini** - Google Gemini 1.5 Pro (universal JSON prompt)
- **ChatGPT** - OpenAI GPT-4o (Structured Outputs - 100% guarantee)
- **Grok** - xAI Grok (OpenAI-compatible)
- **Kimi** - Moonshot AI (OpenAI-compatible)

Enter API key or configure in `st.secrets`

### 2. Customize Prompt (Optional)

Click **"🔧 Vision API Prompt (muudetav)"** to:
- View and edit the default extraction prompt
- Add specific instructions for your document type
- Reset to default if needed
- See extraction method indicator (Structured Outputs vs Universal JSON)

### 3. Upload PDFs

- Upload one or more PDF files (max 10 pages each)
- Files with >10 pages will be rejected (cost protection)

### 4. Process Files

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
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── gwb_timesheet.py   # Pydantic schema for Structured Outputs
│   └── providers/
│       ├── base.py            # AI provider interface
│       ├── gemini_provider.py # Google Gemini (universal JSON)
│       ├── openai_provider.py # OpenAI GPT-4o (Structured Outputs)
│       ├── grok_provider.py   # xAI Grok
│       └── kimi_provider.py   # Moonshot AI Kimi
├── utils/
│   └── io.py                  # XLSX export with formatting
└── requirements.txt
```

## Data Processing Pipeline

1. **Ingest**: Validate page count (≤10)
2. **Convert**: PDF pages to images (300 DPI - optimal for Vision APIs)
3. **Extract**: Vision API analyzes images and returns:
   - **OpenAI Structured Outputs**: Guaranteed schema adherence (all fields extracted)
   - **Gemini Universal Prompt**: Explicit JSON schema with field requirements
   - Column names
   - Row data (as dictionaries)
   - Table metadata (count, confidence)
   - Formatting (merged cells, borders, bold)
4. **Export**: Generate XLSX with visual formatting preserved

## AI Provider Comparison

### OpenAI GPT-4o (Structured Outputs)
- **Model**: `gpt-4o-2024-08-06`
- **Method**: Pydantic schema enforcement
- **Guarantee**: 100% schema adherence - AI **cannot** omit required fields
- **Best for**: Documents with strict structure (GWB timesheets, forms)
- **Pricing**: €4.40 input, €13.20 output (per 1M tokens)

### Gemini 1.5 Pro (Universal JSON)
- **Model**: `gemini-1.5-pro`
- **Method**: Explicit JSON schema in prompt
- **Guarantee**: Best-effort extraction with "NOT_FOUND" fallbacks
- **Best for**: General table extraction, cost-sensitive projects
- **Pricing**: €1.21 input, €4.40 output (per 1M tokens)

### All Provider Pricing (EUR)

| Provider | Input (1M tokens) | Output (1M tokens) |
|----------|-------------------|-------------------|
| Gemini 1.5 Pro | €1.21 | €4.40 |
| GPT-4o | €4.40 | €13.20 |
| Grok | €4.40 | €13.20 |
| Kimi | €1.56 | €1.56 |

## Custom Prompts

The prompt editor allows you to customize extraction instructions:

**Default OpenAI Prompt** (Structured Outputs):
```
Extract ALL data from this GWB Monthly Time Sheet document.

This document has 5 main sections that you MUST extract:

1. SERVICE PROVIDER DETAILS (blue header section)
2. CONTRACT INFORMATION (blue header section)
3. TIMESHEET DETAILS (blue header section)
4. SUMMARY TABLE (Effort for Normal Working Hours)
5. DAILY CALENDAR (days 1-31)

The response will be automatically structured according to the defined JSON schema.
```

**Default Gemini Prompt** (Universal JSON):
```
Extract ALL data from this GWB Monthly Time Sheet document in structured JSON format.

IMPORTANT: This document has 5 main sections - you MUST extract data from ALL of them:

SECTION 1: SERVICE PROVIDER DETAILS (blue header box)
SECTION 2: CONTRACT INFORMATION (blue header box)
SECTION 3: TIMESHEET DETAILS (blue header box)
SECTION 4: SUMMARY TABLE (Effort for Normal Working Hours)
SECTION 5: DAILY CALENDAR (days 1-31)

CRITICAL RULES:
1. If a field is not found or unreadable, use "NOT_FOUND" instead of omitting it
2. For small numbers (0 vs 8): "8" has TWO loops with middle line, "0" is ONE oval
3. Empty calendar cells should be null, not "0"
4. Extract data from ALL 5 sections - do not skip any section

Return valid JSON ONLY (no markdown, no explanations)...
```

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
- **DPI**: 300 DPI (optimal - avoids Gemini downscaling)
- **Batch processing**: Processes multiple files sequentially
- **Cost tracking**: Real-time token usage and EUR cost per file
- **No validation**: Exports exactly what Vision API returns (no data modification)

## GWB Timesheet Extraction

This application is optimized for **GWB Monthly Time Sheet** documents with:

### Document Structure (5 Sections)
1. **SERVICE PROVIDER DETAILS** (5 fields)
   - Service Provider name
   - Start Date
   - Type (QTM/GTM)
   - Profile
   - Place of Delivery

2. **CONTRACT INFORMATION** (7 fields)
   - Specific Contract Number
   - Contract Start/End Dates
   - Lot No
   - Contractor Name
   - Framework Contract Number
   - Program

3. **TIMESHEET DETAILS** (3 fields)
   - Service Request Number
   - Service Request Start/End Dates

4. **SUMMARY TABLE**
   - Contractual/Available/Consumed/Remaining Days (Onsite/Offsite)

5. **DAILY CALENDAR**
   - Hours per day (1-31)
   - Values: 0, 8, OFF, ON, or empty

### Extraction Guarantee
- **OpenAI**: 100% schema adherence - all 15 metadata fields + tables
- **Gemini**: Best-effort with "NOT_FOUND" fallbacks

## Version History

- **v3.2.1** (Current) - Bug fix: Missing Optional import
- **v3.2.0** - Added custom prompt editor in Streamlit UI
- **v3.1.0** - Implemented OpenAI Structured Outputs (100% schema adherence)
- **v3.0.3** - Added Pydantic schemas for GWB timesheet structure
- **v3.0.2** - DPI optimization (300 DPI to avoid Gemini downscaling)
- **v3.0.0** - Universal PDF table extractor (removed validation, quarterly reports)
- **v2.1.2** - Bug fix: Show warnings even when processing fails
- **v2.1.0** - Added Vision API formatting preservation
- **v2.0.0** - Added AI Vision API support
- **v1.0.0** - Initial release with rule-based extraction

## Current Status & Next Steps

### ✅ Completed
- OpenAI Structured Outputs integration (100% guarantee)
- Pydantic schema for GWB timesheet (5 sections, 15+ fields)
- Custom prompt editor in Streamlit sidebar
- Gemini universal JSON prompt
- DPI optimization (300 DPI)
- Multi-table XLSX export support

### 🔄 Testing Phase
- Verify GWB1.pdf extraction quality (all 15 metadata fields)
- Compare OpenAI vs Gemini accuracy
- Test prompt editor modifications
- Validate XLSX formatting output

### 📋 Known Issues
- None currently

### 💡 Future Enhancements
- Add more AI providers (Claude, Llama Vision)
- Batch prompt templates for common document types
- Export format options (CSV, JSON)
- OCR quality metrics dashboard

## Troubleshooting

### Vision API not extracting all fields?
1. Try **OpenAI with Structured Outputs** - 100% schema guarantee
2. Edit the prompt to add specific field instructions
3. Check image quality (300 DPI recommended)

### High API costs?
1. Use **Gemini** instead of OpenAI (3x cheaper)
2. Reduce page count (max 10 pages enforced)
3. Process only necessary files

### Prompt modifications not working?
1. Click "🔄 Taasta vaikeprompt" to reset
2. Check for JSON syntax errors in custom prompt
3. Test with small sample PDF first

## License

MIT

## Contact

For questions or issues, please open a GitHub issue at:
https://github.com/henrikaavik/PDF-OCR-testing/issues
