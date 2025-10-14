## Mira - Setup and Run

This guide helps you set up Mira locally: create a virtual environment, install dependencies, configure your API key, and run either the CLI chat or the API server.

### Prerequisites

- Python 3.10+ (tested with 3.13)
- An API key for Google Gemini (GEMINI_API_KEY)
- A Pinecone API key (PINECONE_API_KEY) for RAG capabilities

### 1) Clone and enter the project

```bash
git clone <your-fork-or-repo-url>
cd Mira
```

### 2) Create and activate a virtual environment

Windows (PowerShell):

```powershell
python -m venv venv
./venv/Scripts/Activate.ps1
```

macOS/Linux (bash/zsh):

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3) Install dependencies

```bash
pip install -r requirements.txt
```

### 4) Configure environment variables

Create a `.env` file in the project root with your API keys:

```env
GEMINI_API_KEY=your_gemini_api_key_here
PINECONE_API_KEY=your_pinecone_api_key_here
```

The app loads this automatically via `dotenv` (see `agents/config/llm_config.py`).

### 5) Setup RAG System (Optional but Recommended)

Mira includes powerful RAG capabilities for searching through company policy documents:

```bash
# Setup the vector store with policy documents
python setup_rag.py

# Test the RAG system
python test_mira.py
```

This will process all PDF documents in `agents/docs/` and make them searchable.

### 6A) Run the CLI chat

From the project root:

```bash
python agents/mira/test.py
```

Type your message; enter `exit` or `quit` to stop.

If you see import warnings in your IDE but it runs fine, ensure you run from the project root so relative imports resolve. If needed, set `PYTHONPATH`:

Windows (PowerShell):

```powershell
$env:PYTHONPATH="."; python agents/mira/test.py
```

macOS/Linux:

```bash
PYTHONPATH=. python agents/mira/test.py
```

### 6B) Run the API server (optional)

The FastAPI app lives under `server/main.py`.

```bash
uvicorn server.main:app --reload
```

Then open `http://127.0.0.1:8000`.

### Sub-agents (HR, IT, RM)

- Sub-agents live in `agents/mira/sub_agents/<agent_name>/` with `prompts.py`, `tools.py`, and `agent.py`.
- The main agent exposes them as tools via `agents/mira/tools.py`.
- To add new tools, define `@tool` functions in the sub-agent’s `tools.py` and add them to the `*_TOOLS` list; the sub-agent agent will pick them up automatically.

### Notes

- The HR leave workflow tools are currently stubs (e.g., calendar conflict checks, supervisor approvals) and are designed to be wired to Google APIs later.
- Keep your virtual environment activated whenever you run scripts.
