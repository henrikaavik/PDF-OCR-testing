# Development Status & Technical Notes

**Last Updated**: 2025-11-09
**Current Version**: v3.2.1
**Status**: ✅ Production Ready - Testing Phase

---

## Quick Context for Continuation

### What This Project Does
Universal PDF table extractor using AI Vision APIs (Gemini, OpenAI GPT-4o). Converts PDF tables to XLSX with formatting preservation. Optimized for **GWB Monthly Time Sheet** documents with 5 distinct sections.

### Current State
- ✅ Core functionality working (multi-file processing, AI extraction, XLSX export)
- ✅ OpenAI Structured Outputs (100% schema adherence)
- ✅ Gemini universal JSON prompt
- ✅ Custom prompt editor in Streamlit UI
- 🔄 Testing extraction quality with real GWB documents

---

## Recent Development History (v3.0.0 → v3.2.1)

### v3.2.1 (2025-11-09) - Bug Fix
**Problem**: `NameError: name 'Optional' is not defined`
**Fix**: Added `Optional` to typing imports in `streamlit_app.py:8`
**Commit**: f826258

### v3.2.0 (2025-11-09) - Custom Prompt Editor
**Added**:
- Prompt editor in Streamlit sidebar (expandable section)
- Session state persistence for custom prompts
- Provider-specific default prompts (`get_default_prompt()` classmethod)
- Reset to default button
- Indicator showing extraction method (Structured Outputs vs Universal JSON)

**Files Modified**:
- `streamlit_app.py` - Added prompt editor UI (lines 206-246)
- `core/providers/openai_provider.py` - Added `get_default_prompt()` classmethod
- `core/providers/gemini_provider.py` - Added `get_default_prompt()` classmethod

### v3.1.0 (2025-11-09) - OpenAI Structured Outputs
**Problem**: Vision API was missing entire document sections (blue header metadata fields)
**Root Cause**: Prompt said "Extract ALL data from ALL **tables**" - AI ignored non-tabular key-value pairs
**Solution**: OpenAI Structured Outputs with Pydantic schema enforcement

**Added**:
- `core/schemas/gwb_timesheet.py` - Pydantic schema (5 sections, 15+ fields)
- `core/schemas/__init__.py` - Package initialization
- OpenAI provider refactored to use `client.beta.chat.completions.parse()`
- `_convert_structured_to_legacy()` method for backward compatibility
- Gemini provider updated with explicit JSON schema prompt

**Files Created**:
- `core/schemas/__init__.py`
- `core/schemas/gwb_timesheet.py`

**Files Modified**:
- `core/providers/openai_provider.py` - Complete refactor (Structured Outputs API)
- `core/providers/gemini_provider.py` - Universal JSON prompt
- `requirements.txt` - Added `pydantic>=2.0.0`

### v3.0.2 - DPI Optimization
**Change**: PDF to image DPI 450 → 400 → 300
**Reason**: 300 DPI is optimal - avoids Gemini Vision API downscaling

---

## Architecture Overview

### Key Files & Responsibilities

#### Frontend
- **`streamlit_app.py`** (362 lines)
  - Main Streamlit application
  - Provider selection & API key input
  - Custom prompt editor (lines 206-246)
  - File upload & processing orchestration
  - Results display & XLSX download
  - Entry point: `process_single_pdf()` → provider → XLSX export

#### Core Processing
- **`core/ingest.py`**
  - Page count validation (max 10 pages)
  - `PageLimitExceededError` exception

- **`core/ocr.py`**
  - PDF to images conversion using `pdf2image`
  - DPI: 300 (optimal for Vision APIs)

#### AI Providers
- **`core/providers/base.py`**
  - `AIProvider` abstract base class
  - Metrics tracking (tokens, cost, latency)
  - Pricing calculation in EUR

- **`core/providers/openai_provider.py`** (258 lines)
  - Model: `gpt-4o-2024-08-06`
  - **Structured Outputs**: Uses Pydantic schema enforcement
  - Method: `client.beta.chat.completions.parse()`
  - Guarantee: 100% schema adherence
  - `get_default_prompt()`: Returns OpenAI-specific prompt
  - `_convert_structured_to_legacy()`: Converts Pydantic → legacy format
  - Pricing: €4.40 input, €13.20 output (per 1M tokens)

- **`core/providers/gemini_provider.py`** (271 lines)
  - Model: `gemini-1.5-pro`
  - **Universal JSON Prompt**: Explicit schema in prompt
  - Method: `vision_model.generate_content()`
  - Guarantee: Best-effort with "NOT_FOUND" fallbacks
  - `get_default_prompt()`: Returns Gemini-specific prompt
  - Pricing: €1.21 input, €4.40 output (per 1M tokens)

- **`core/providers/grok_provider.py`**
  - xAI Grok (OpenAI-compatible API)

- **`core/providers/kimi_provider.py`**
  - Moonshot AI Kimi (OpenAI-compatible API)

#### Schemas
- **`core/schemas/gwb_timesheet.py`** (116 lines)
  - Pydantic models for GWB Monthly Time Sheet
  - 5 main sections:
    1. `ServiceProviderDetails` (5 fields)
    2. `ContractInformation` (7 fields)
    3. `TimesheetDetails` (3 fields)
    4. `SummaryTable` (rows with 8 columns)
    5. `DailyCalendar` (rows with 31 day columns)
  - Root model: `GWBTimesheet`

#### Export
- **`utils/io.py`**
  - `create_per_file_xlsx()`: Generates XLSX with formatting
  - Multi-table support (separate sheets or sections)
  - Formatting preservation (borders, merged cells, bold)

---

## Data Flow

```
User uploads PDF
    ↓
streamlit_app.py: process_single_pdf()
    ↓
core/ingest.py: ingest_pdf() - validate page count (≤10)
    ↓
core/ocr.py: pdf_to_images() - convert to images (300 DPI)
    ↓
FOR EACH PAGE:
    ↓
    provider.extract_table_from_image(image_bytes, custom_prompt)
        ↓
        [OpenAI Path]
        client.beta.chat.completions.parse(
            response_format=GWBTimesheet  ← Pydantic schema
        )
        ↓
        _convert_structured_to_legacy() → legacy format

        [Gemini Path]
        vision_model.generate_content([prompt, image])
        ↓
        Parse JSON response → legacy format
    ↓
    Collect: rows, columns, tables, formatting
    ↓
utils/io.py: create_per_file_xlsx()
    ↓
Download XLSX file
```

---

## GWB Timesheet Structure

### 5 Document Sections

#### 1. SERVICE PROVIDER DETAILS (Blue Header Box)
- `service_provider` - Name (SURNAME, Name)
- `service_provider_start_date` - dd/mm/yyyy
- `type` - QTM, GTM, etc.
- `profile` - Job title/role
- `place_of_delivery` - Location

#### 2. CONTRACT INFORMATION (Blue Header Box)
- `specific_contract_number`
- `specific_contract_start_date` - dd/mm/yyyy
- `specific_contract_end_date` - dd/mm/yyyy
- `lot_no`
- `contractor_name` - Company
- `framework_contract_number`
- `program` - Program name

#### 3. TIMESHEET DETAILS (Blue Header Box)
- `service_request_number` - e.g., SR2
- `service_request_start_date` - dd/mm/yyyy
- `service_request_end_date` - dd/mm/yyyy

#### 4. SUMMARY TABLE
**Title**: "Effort for Normal Working Hours (h)"

**Columns**:
- Service Request
- Contractual Days (Onsite/Offsite)
- Available Days (Onsite/Offsite)
- Consumed Days (Onsite/Offsite)
- Remaining Days (Onsite/Offsite)

#### 5. DAILY CALENDAR
**Columns**: Service Request, day_1, day_2, ..., day_31

**Values**: 0, 8, OFF, ON, or null (empty)

---

## Extraction Methods Comparison

### OpenAI Structured Outputs (Recommended for GWB)
✅ **Guarantee**: 100% schema adherence - AI cannot omit required fields
✅ **Method**: Pydantic schema enforcement via `response_format` parameter
✅ **Best for**: Documents with strict structure (forms, timesheets)
❌ **Cost**: 3x more expensive than Gemini (€4.40 vs €1.21 input)
❌ **Flexibility**: Schema changes require code deployment

**Technical Details**:
```python
response = self.client.beta.chat.completions.parse(
    model="gpt-4o-2024-08-06",
    messages=[{"role": "user", "content": [prompt, image]}],
    response_format=GWBTimesheet,  # Pydantic model
    temperature=0.0
)
timesheet = response.choices[0].message.parsed  # Guaranteed structure
```

### Gemini Universal JSON Prompt
✅ **Cost**: 3x cheaper (€1.21 input vs €4.40)
✅ **Flexibility**: Prompt changes via UI (no code deployment)
⚠️ **Guarantee**: Best-effort with "NOT_FOUND" fallbacks
❌ **Risk**: May skip sections if not explicitly prompted

**Technical Details**:
```python
response = self.vision_model.generate_content(
    [prompt, image],  # Explicit JSON schema in prompt
    generation_config=genai.types.GenerationConfig(temperature=0.0)
)
# Parse JSON manually with fallback handling
```

---

## Custom Prompt Editor

### Location
Streamlit sidebar → **"🔧 Vision API Prompt (muudetav)"** expander

### Features
- View/edit default provider prompt
- Session state persistence (`st.session_state.custom_prompt`)
- Reset to default button
- Extraction method indicator:
  - OpenAI: "✓ Structured Outputs (100%)"
  - Gemini: "ℹ️ Universal JSON prompt"

### Usage
1. Click expander to open editor
2. Modify prompt text
3. Click "🔄 Taasta vaikeprompt" to reset (triggers `st.rerun()`)
4. Process PDFs - custom prompt is passed through pipeline

### Implementation
```python
# streamlit_app.py lines 206-246

# Get default from provider
if provider_type == "gemini":
    from core.providers.gemini_provider import GeminiProvider
    default_prompt = GeminiProvider.get_default_prompt()
elif provider_type == "openai":
    from core.providers.openai_provider import OpenAIProvider
    default_prompt = OpenAIProvider.get_default_prompt()

# Initialize session state
if 'custom_prompt' not in st.session_state:
    st.session_state.custom_prompt = default_prompt

# Editable text area
custom_prompt = st.text_area(
    "Prompt:",
    value=st.session_state.custom_prompt,
    height=300,
    key="prompt_editor"
)

# Pass to processing
result = process_single_pdf(filename, file_bytes, provider, custom_prompt)
```

---

## Common Issues & Solutions

### Issue 1: Missing Fields in Extraction
**Symptoms**: XLSX file missing blue header metadata (SERVICE PROVIDER DETAILS, etc.)
**Root Cause**: Old prompt focused only on "tables" - ignored key-value pairs
**Solution**: Use OpenAI Structured Outputs (100% guarantee) OR update Gemini prompt with explicit field list

### Issue 2: 0 vs 8 Confusion
**Symptoms**: Daily calendar shows "0" instead of "8" or vice versa
**Root Cause**: Vision API misreading small numbers
**Solution**: Prompt includes rule: "8 has TWO loops with middle line, 0 is ONE oval"

### Issue 3: Empty Cells as "0"
**Symptoms**: Empty calendar cells filled with "0" instead of null
**Root Cause**: Vision API defaulting to "0" for empty cells
**Solution**: Prompt includes rule: "Empty calendar cells should be null, not '0'"

### Issue 4: High API Costs
**Symptoms**: Processing costs too high
**Solution**: Switch from OpenAI (€4.40) to Gemini (€1.21) - 3x cheaper

### Issue 5: Streamlit Deployment Errors
**Symptoms**: `NameError`, `ImportError`, etc.
**Recent Fix**: Missing `Optional` import in `streamlit_app.py:8` (v3.2.1)
**Solution**: Check all type hints have corresponding imports

---

## Testing Checklist

### Manual Testing (Recommended Before Next Session)
- [ ] Upload GWB1.pdf with OpenAI provider
- [ ] Verify all 15 metadata fields extracted (5+7+3)
- [ ] Check XLSX has 3 tables: Metadata, Summary, Daily Calendar
- [ ] Upload same file with Gemini provider
- [ ] Compare OpenAI vs Gemini accuracy
- [ ] Test prompt editor: modify prompt → process → reset → process
- [ ] Verify cost tracking matches expected values

### Edge Cases
- [ ] PDF with >10 pages (should reject)
- [ ] PDF with missing sections (e.g., no daily calendar)
- [ ] Empty fields (should show "NOT_FOUND" or null)
- [ ] Multi-page documents (formatting offsets correct?)

---

## Known Limitations

1. **Page Limit**: 10 pages per PDF (hard limit for cost protection)
2. **Schema Changes**: OpenAI Structured Outputs requires code deployment for schema updates
3. **Gemini Guarantee**: No 100% guarantee - best-effort extraction
4. **Single Document Type**: Optimized for GWB timesheets (not generic)
5. **No OCR Fallback**: If Vision API fails, no text-based fallback

---

## Future Enhancements (Ideas)

### High Priority
- [ ] Add extraction quality metrics (% fields extracted, confidence scores)
- [ ] Multi-document type support (templates for different PDFs)
- [ ] Claude Vision API integration (Anthropic)
- [ ] Export validation report (missing fields, low-confidence values)

### Medium Priority
- [ ] Batch prompt templates (dropdown selection)
- [ ] CSV/JSON export options
- [ ] OCR quality dashboard
- [ ] Cost estimation before processing

### Low Priority
- [ ] Llama Vision API integration
- [ ] Historical cost tracking (database)
- [ ] A/B testing interface (compare providers)
- [ ] API endpoint for programmatic access

---

## Critical Code Sections (For Quick Reference)

### OpenAI Structured Outputs Integration
**File**: `core/providers/openai_provider.py`
**Lines**: 101-138

```python
# Use Structured Outputs API
from core.schemas.gwb_timesheet import GWBTimesheet

response = self.client.beta.chat.completions.parse(
    model=self.vision_model,
    messages=[...],
    response_format=GWBTimesheet,  # Pydantic enforcement
    temperature=0.0
)

timesheet = response.choices[0].message.parsed
return self._convert_structured_to_legacy(timesheet)
```

### Legacy Format Conversion
**File**: `core/providers/openai_provider.py`
**Lines**: 173-257

```python
def _convert_structured_to_legacy(self, timesheet) -> Dict[str, Any]:
    """Convert Pydantic GWBTimesheet to legacy format."""

    # Create 3 tables:
    # 1. Metadata (SERVICE PROVIDER DETAILS, CONTRACT INFO, TIMESHEET DETAILS)
    # 2. Summary Table (Effort for Normal Working Hours)
    # 3. Daily Calendar (days 1-31)

    metadata_rows = []
    # Extract all metadata fields...

    return {
        'tables': tables,  # NEW: Separate tables
        'columns': all_columns,  # LEGACY
        'rows': all_rows,  # LEGACY
        'formatting': {},  # LEGACY
        'success': True
    }
```

### Custom Prompt Integration
**File**: `streamlit_app.py`
**Lines**: 304-310

```python
# Get custom prompt from session state
custom_prompt = st.session_state.get('custom_prompt', None)

results = []
for filename, file_bytes in files_to_process:
    result = process_single_pdf(filename, file_bytes, provider, custom_prompt)
    results.append(result)
```

---

## Git Workflow

### Recent Commits
```
f826258 - Fix NameError: Add Optional to typing imports (v3.2.1)
e27d02a - Add custom prompt editor to Streamlit UI (v3.2.0)
[earlier] - Implement OpenAI Structured Outputs (v3.1.0)
```

### Branch
- `main` - Production branch (deployed to Streamlit Cloud)

### Deployment
- **Platform**: Streamlit Cloud
- **URL**: (Check Streamlit Cloud dashboard)
- **Auto-deploy**: Enabled on push to `main`

---

## Quick Start Commands

### Local Development
```bash
cd /Users/henrikaavik/progemoge/t88lehed-tabelina
streamlit run streamlit_app.py
```

### Git Operations
```bash
# Status
git status

# Commit + Push
git add .
git commit -m "Description"
git push

# View recent commits
git log --oneline -5
```

### Dependencies
```bash
# Install/update
pip install -r requirements.txt

# Check installed versions
pip show streamlit pydantic openai google-generativeai
```

---

## Contact & Resources

- **GitHub Repo**: https://github.com/henrikaavik/PDF-OCR-testing
- **Streamlit Docs**: https://docs.streamlit.io
- **OpenAI Structured Outputs**: https://platform.openai.com/docs/guides/structured-outputs
- **Pydantic Docs**: https://docs.pydantic.dev

---

## Next Session Quick Start

**If continuing extraction quality work**:
1. Test GWB1.pdf with OpenAI provider
2. Check XLSX output for all 15 metadata fields
3. Compare with Gemini extraction
4. Document findings in GitHub issue or this file

**If adding new features**:
1. Review "Future Enhancements" section
2. Create feature branch: `git checkout -b feature/name`
3. Implement, test, merge to main
4. Update version in `streamlit_app.py` and this file

**If debugging issues**:
1. Check "Common Issues & Solutions" section
2. Review recent commits: `git log --oneline -10`
3. Test locally before pushing to production
4. Update "Known Issues" section in README if needed

---

**End of Development Status Document**
