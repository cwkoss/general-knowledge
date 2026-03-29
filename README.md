# Perknow

A personal knowledge management system with AI-assisted organization. Capture raw ideas through a web interface, which are immediately persisted to SQLite. A background "AI Gardener" processes notes to extract titles, generate embeddings, suggest links, and propose tags. All AI suggestions are reviewed before being finalized. The system exports to hierarchical markdown files tracked in git for long-term durability.

## Features

- **Immediate Persistence**: Ideas saved instantly to SQLite
- **AI Gardener**: Background processing for:
  - Title extraction
  - Embedding generation
  - Similar note finding
  - Link suggestions
  - Tag suggestions
- **Human-in-the-Loop**: Review and approve/reject all AI suggestions
- **Markdown Export**: Human-readable backup with YAML frontmatter
- **Git Integration**: Version history for your knowledge base

## Quick Start

### Prerequisites

1. **Python 3.9+** installed
2. **Ollama** installed and running (https://ollama.com/download)
3. Required models pulled:
   ```bash
   ollama pull nomic-embed-text
   ollama pull llama3.2
   ```

### One-Command Start (Recommended)

```powershell
# PowerShell (recommended - has automatic port detection)
.\start-perknow.ps1

# Or with a specific starting port
.\start-perknow.ps1 -StartPort 9000

# Skip auto-opening browser
.\start-perknow.ps1 -NoBrowser
```

```cmd
:: Command Prompt
start-perknow.bat
```

### Manual Start

```bash
# Terminal 1: Initialize directories and git
mkdir -p data export
mkdir -p data export
cd export && git init && cd ..

# Terminal 1: Start AI gardener worker
python scripts/gardener_worker.py

# Terminal 2: Start web server (auto-finds available port)
uvicorn perknow.main:app --reload --port 8003

# Open browser to http://localhost:8003
```

## Project Structure

```
perknow/
├── perknow/              # Main Python package
│   ├── main.py           # FastAPI application
│   ├── database.py       # SQLite operations
│   ├── llm_client.py     # Ollama integration
│   ├── gardener.py       # AI processing logic
│   ├── exporter.py       # Markdown export
│   └── templates/        # HTMX + Jinja2 templates
├── scripts/
│   └── gardener_worker.py # Background AI processor
├── data/                 # SQLite database (gitignored)
├── export/               # Markdown + Git backup
├── start-perknow.ps1     # Quick start script (PowerShell)
├── start-perknow.bat     # Quick start script (CMD)
└── requirements.txt      # Python dependencies
```

## Usage

### 1. Capture Ideas (`/inbox`)

1. Open http://localhost:8003
2. Type your raw idea in the textarea
3. Click "Plant Idea"
4. The note is immediately saved to SQLite and exported to `export/inbox/`

### 2. AI Processing (Background)

The gardener worker automatically:
- Extracts a concise title
- Generates vector embeddings
- Finds similar notes
- Suggests relevant links
- Proposes tags

All suggestions are marked as `ai_suggested=TRUE, user_approved=FALSE`

### 3. Review Suggestions (`/review`)

1. Navigate to the Review page
2. See all pending AI suggestions
3. Click ✅ to approve or ❌ to reject each suggestion
4. Approved suggestions update the markdown export

### 4. Browse & Navigate (`/browse`, `/note/{id}`)

- Browse all notes with pagination
- Click any note to view full details
- See outbound links and backlinks
- View and manage tags

### 5. Markdown Export

All approved notes are exported to `export/` with:
- YAML frontmatter (id, title, timestamps, tags)
- Wiki-style links: `[[Related Note]]`
- Git version history

## Configuration

Create a `.env` file to customize:

```bash
DATABASE_PATH=data/perknow.db
EXPORT_PATH=export/
OLLAMA_BASE_URL=http://localhost:11434
EMBEDDING_MODEL=nomic-embed-text
CHAT_MODEL=llama3.2
GARDENER_POLL_INTERVAL=5.0
EMBEDDING_DIMENSIONS=768
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Redirect to inbox |
| GET | `/inbox` | Capture new ideas |
| POST | `/api/plant` | Create note & queue AI processing |
| GET | `/browse` | List all notes |
| GET | `/note/{id}` | View single note |
| GET | `/review` | Review AI suggestions |
| POST | `/api/approve-link/{id}` | Approve link suggestion |
| POST | `/api/reject-link/{id}` | Reject link suggestion |
| POST | `/api/approve-tag/{id}` | Approve tag suggestion |
| POST | `/api/reject-tag/{id}` | Reject tag suggestion |
| GET | `/health` | Health check |

## Development

### Run Tests
```bash
pytest tests/
```

### Database Schema

See `perknow/database.py` for full schema. Main tables:
- `notes` - Note content, embeddings, status
- `links` - Bidirectional note relationships
- `tags` - Note categorization
- `gardening_queue` - Background AI processing jobs

### Adding New Gardener Operations

1. Add operation type in `perknow/gardener.py::OperationType`
2. Implement handler in `Gardener.process_queue_item()`
3. Queue operation when planting note in `main.py::api_plant()`

## Architecture

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   Browser   │──────▶│  FastAPI     │──────▶│   SQLite    │
│  (HTMX)     │◀──────│  (perknow)   │◀──────│  (perknow)  │
└─────────────┘      └──────────────┘      └──────┬──────┘
       │                    │                      │
       │                    ▼                      │
       │              ┌──────────────┐             │
       └─────────────▶│  Markdown    │◀────────────┘
                      │  Export      │
                      │  (Git)       │
                      └──────────────┘
                             ▲
                             │
                      ┌──────────────┐
                      │  AI Gardener │
                      │  (Ollama)    │
                      └──────────────┘
```

## Troubleshooting

### Port Already in Use

The quick start script automatically finds an available port. If running manually:

```bash
# Find available port
netstat -ano | findstr :8000

# Use different port
uvicorn perknow.main:app --port 8003
```

### Ollama Connection Error

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama
ollama serve

# Pull required models
ollama pull nomic-embed-text
ollama pull llama3.2
```

### Gardener Not Processing

1. Check gardener is running: `python scripts/gardener_worker.py`
2. Check queue: Look at `gardening_queue` table in SQLite
3. Check Ollama is responding: Test with `curl`

### Database Locked

SQLite doesn't support concurrent writes. Ensure only one process writes to the database at a time.

## License

MIT License - See LICENSE file

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## Acknowledgments

- [Ollama](https://ollama.com/) - Local LLM inference
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [HTMX](https://htmx.org/) - Frontend interactivity
- [SQLite](https://sqlite.org/) - Embedded database
