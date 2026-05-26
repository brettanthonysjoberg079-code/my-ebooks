```markdown name=README.md url=https://github.com/brettanthonysjoberg079-code/my-ebooks/blob/main/README.md
# Ebook Production Pipeline

A modular, automated Python-based system for generating, compiling, tracking, and reviewing ebooks using AI, open-source tools, and cloud services.

## Architecture Overview

```
┌─────────────────┐
│  LLM Services   │
│  • OpenAI       │
│  • OpenRouter   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────────┐
│  Content Gen    │─────▶│  Markdown Files  │
│  (LLMService)   │      │  (Temporary)     │
└─────────────────┘      └────────┬─────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │  Pandoc         │
                         │  (Compiler)     │
                         └────────┬────────┘
                                  │
                    ┌─────────────┴──────────────┐
                    ▼                            ▼
            ┌──────────────┐          ┌──────────────┐
            │   EPUB File  │          │   PDF File   │
            └──────┬───────┘          └──────┬───────┘
                   │                         │
                   └─────────────┬───────────┘
                                 │
                                 ▼
                        ┌──────────────────┐
                        │  Airtable        │
                        │  (Metadata Log)  │
                        └──────┬───────────┘
                               │
                               ▼
                        ┌──────────────────┐
                        │  Google Tasks    │
                        │  (Review Queue)  │
                        └──────────────────┘
```

## Features

✅ **Multi-Provider LLM Support**: Seamlessly switch between OpenAI (GPT-4) and OpenRouter (open-weights models)  
✅ **Professional Ebook Compilation**: Full EPUB + PDF support via Pandoc with metadata injection  
✅ **Fault-Tolerant State Tracking**: Airtable with automatic JSON fallback when API unavailable  
✅ **Human Review Workflows**: Google Tasks integration for quality assurance  
✅ **Dataset Integration**: Pull semantic analysis datasets from HuggingFace Hub  
✅ **CI/CD Ready**: GitHub Actions workflow for scheduled/manual execution  
✅ **Comprehensive Logging**: JSON audit trails with execution reports  

## Quick Start

### 1. Installation

```bash
git clone https://github.com/yourusername/my-ebooks
cd my-ebooks

# Install dependencies
pip install -r requirements.txt

# Install Pandoc (required)
# macOS:
brew install pandoc

# Ubuntu/Debian:
sudo apt-get install pandoc

# Windows (via Chocolatey):
choco install pandoc
```

### 2. Environment Configuration

```bash
# Copy template
cp .env.example .env

# Edit with your credentials
OPENAI_API_KEY=sk-your-key-here
OPENROUTER_API_KEY=your-openrouter-key
AIRTABLE_TOKEN=pat_your-token
AIRTABLE_BASE_ID=appXXXXXXXXXXXXXX
HUGGINGFACE_TOKEN=hf_your-token
GOOGLE_SERVICE_ACCOUNT_JSON=/path/to/service-account.json
```

### 3. Local Execution

```bash
# Run the pipeline
python main.py

# Output will be generated in:
# - ./output/          (EPUB/PDF files)
# - ./logs/            (Execution reports)
# - ./state/           (Fallback JSON cache)
```

### 4. GitHub Actions Setup

1. **Create repository secrets** (Settings → Secrets and variables):
   - `OPENAI_API_KEY`
   - `OPENROUTER_API_KEY`
   - `AIRTABLE_TOKEN`
   - `AIRTABLE_BASE_ID`
   - `HUGGINGFACE_TOKEN`
   - `GOOGLE_TASKS_LIST_ID`
   - `GOOGLE_SERVICE_ACCOUNT_JSON`

2. **Trigger pipeline**:
   ```bash
   # Via GitHub CLI
   gh workflow run pipeline.yml
   
   # Via API
   curl -X POST https://api.github.com/repos/OWNER/REPO/dispatches \
     -H "Authorization: token YOUR_PAT" \
     -H "Accept: application/vnd.github.v3+raw" \
     -d '{"event_type":"trigger-pipeline"}'
   ```

3. **Schedule execution** (already configured for Monday 9 AM UTC):
   - Edit `.github/workflows/pipeline.yml` to adjust cron schedule

## Service Modules

### `services/llm_service.py`
Unified LLM interface with provider abstraction.

```python
from services import LLMService

llm = LLMService()

# Creative writing
response = llm.generate_creative_content(
    prompt="Write a chapter about...",
    max_tokens=2048,
    temperature=0.7
)

# Structured data extraction
response = llm.extract_structured_data(
    content="Book content...",
    extraction_prompt="Extract all character names",
    output_format="json"
)

# Semantic editing
response = llm.semantic_edit(
    original_text="...",
    editing_instruction="Make this more formal"
)
```

### `services/compiler_service.py`
Pandoc subprocess wrapper for EPUB/PDF compilation.

```python
from services import PandocCompiler

compiler = PandocCompiler()

# Compile to EPUB
result = compiler.compile_to_epub(
    source_file="chapter1.md",
    metadata={"title": "My Book", "author": "John Doe"}
)

# Compile to PDF
result = compiler.compile_to_pdf(
    source_file="chapter1.md",
    metadata={"title": "My Book"}
)

# Batch processing
results = compiler.compile_batch(
    source_files=["ch1.md", "ch2.md"],
    format_types=["epub", "pdf"]
)

# Save audit log
compiler.save_compilation_log(results)
```

### `services/airtable_service.py`
Airtable CRUD with local JSON fallback.

```python
from services import AirtableService

airtable = AirtableService()

# Create record
record = airtable.create_record(
    title="My Ebook",
    author="Jane Doe",
    niche="Self-Help",
    status="compiled",
    render_path="./output/my_ebook.epub"
)

# Update record
airtable.update_record(
    record_id=record.id,
    updates={"Current Status": "published"}
)

# List records
books = airtable.list_records(
    filter_formula="{Current Status} = 'compiled'"
)

# Get cache summary
summary = airtable.get_cache_summary()
```

### `services/task_service.py`
Google Tasks for human review workflows.

```python
from services import GoogleTasksService

tasks = GoogleTasksService()

# Create review task
task = tasks.create_review_task(
    book_title="My Ebook",
    book_id="rec_12345",
    render_path="./output/my_ebook.epub"
)

# List pending tasks
pending = tasks.list_tasks(completed=False)

# Mark complete
tasks.complete_task(task_id=task.id)
```

### `services/hf_service.py`
HuggingFace Hub dataset/model access.

```python
from services import HuggingFaceService

hf = HuggingFaceService()

# Search datasets
datasets = hf.list_datasets(search_query="books", limit=10)

# Download dataset
path = hf.download_dataset(
    repo_id="wikitext/wikitext-103"
)

# Search models
models = hf.search_models(query="text-generation", limit=5)
```

## Configuration Reference

All configuration is managed via `config.py` using Pydantic:

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | (required) |
| `OPENAI_BASE_URL` | OpenAI endpoint | `https://api.openai.com/v1` |
| `OPENROUTER_API_KEY` | OpenRouter API key | (optional) |
| `OPENROUTER_BASE_URL` | OpenRouter endpoint | `https://openrouter.ai/api/v1` |
| `AIRTABLE_TOKEN` | Airtable PAT | (required) |
| `AIRTABLE_BASE_ID` | Airtable Base ID | (required) |
| `AIRTABLE_TABLE_NAME` | Table name | `Books` |
| `HUGGINGFACE_TOKEN` | HF Hub token | (optional) |
| `PANDOC_PATH` | Pandoc executable | `pandoc` |
| `PANDOC_DEFAULTS_DIR` | Pandoc config dir | `./pandoc_defaults` |
| `PIPELINE_LOG_DIR` | Log output directory | `./logs` |
| `PIPELINE_STATE_DIR` | State cache directory | `./state` |
| `CONTENT_OUTPUT_DIR` | Ebook output dir | `./output` |
| `CONTENT_SOURCE_DIR` | Markdown source dir | `./content` |
| `MAX_RETRIES` | API retry attempts | `3` |
| `REQUEST_TIMEOUT_SECONDS` | HTTP timeout | `30` |

## Pipeline Execution Flow

### Local Execution

```bash
python main.py
```

Output: `logs/pipeline_YYYYMMDD_HHMMSS_report.json`

### GitHub Actions

- **Trigger**: Push, schedule, or manual dispatch
- **Environment**: Ubuntu Latest + Python 3.11
- **Artifacts**: Uploaded logs (30 days) and ebooks (60 days)

## Fault Tolerance & Fallbacks

| Service | Fallback Behavior |
|---------|-------------------|
| Airtable | Local JSON cache in `./state/airtable_fallback.json` |
| Google Tasks | Disabled (no impact on pipeline) |
| HuggingFace | Graceful skip if token missing |
| Pandoc | Pipeline fails (required system dep) |
| LLM | Retry with exponential backoff up to 3x |

## API Documentation

### `EbookPipelineOrchestrator`

```python
orchestrator = EbookPipelineOrchestrator()

# Process single book
result = orchestrator.process_book(
    title="Python for Beginners",
    author="Jane Smith",
    niche="Programming",
    outline=["Chapter 1", "Chapter 2", ...],
    style_guide="Professional tone"
)

# Process batch
report = orchestrator.process_batch([
    {"title": "Book 1", "author": "...", "niche": "...", "outline": [...]},
    {"title": "Book 2", "author": "...", "niche": "...", "outline": [...]},
])
```

## Troubleshooting

### Pandoc not found
```bash
# macOS
brew install pandoc

# Ubuntu
sudo apt-get install pandoc

# Verify
pandoc --version
```

### Airtable API 403 errors
- Verify PAT token has access to the specified Base
- Check Base ID is correct
- Test token: `curl -H "Authorization: Bearer YOUR_TOKEN" https://api.airtable.com/v0/meta/bases`

### LLM rate limits
- Increase `REQUEST_TIMEOUT_SECONDS` in `.env`
- Reduce `MAX_RETRIES` for faster failure
- Switch to OpenRouter for open-weights models with higher limits

### Google Tasks failures (safe to ignore)
- Pipeline continues even if Google Tasks unavailable
- Books compile and log successfully
- Enable/disable via `GOOGLE_TASKS_ENABLED`

## Development

### Running Tests
```bash
# (Test suite to be added)
pytest tests/ -v
```

### Code Style
```bash
black .
flake8 .
```

## License

MIT License - See LICENSE file for details

## Links

- **OpenAI**: https://platform.openai.com
- **OpenRouter**: https://openrouter.ai
- **Airtable API**: https://airtable.com/api
- **HuggingFace**: https://huggingface.co
- **Google Tasks API**: https://developers.google.com/tasks
- **Pandoc**: https://pandoc.org
```
