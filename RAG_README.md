# 🤖 Mira RAG System

Mira now includes powerful RAG (Retrieval-Augmented Generation) capabilities for searching through company policy documents using **completely free** Hugging Face embeddings.

## 🚀 Quick Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `env.example` to `.env` and add your API keys:

```bash
cp env.example .env
```

Edit `.env`:

```bash
PINECONE_API_KEY=your_pinecone_api_key_here
GOOGLE_API_KEY=your_google_api_key_here
```

### 3. Setup Vector Store

```bash
python setup_rag.py
```

### 4. Test the System

```bash
python test_mira.py
```

## 🎯 Usage

```python
from agents.mira.mira import main_agent

# Ask policy questions
response = main_agent("What is the company policy on leave?")
print(response)
```

## 📁 File Structure

```
agents/
├── config/
│   └── pinecone_config.py          # Pinecone configuration
├── docs/                           # PDF policy documents
├── mira/
│   ├── rag_tool.py                # RAG tools
│   ├── tools.py                   # All tools (HR, IT, RM, RAG)
│   └── mira.py                    # Main agent
└── utils/
    ├── document_processor.py      # PDF processing
    └── vector_store_manager.py    # Vector store management
```

## ✨ Features

- **🆓 Completely Free** - No API costs for embeddings
- **⚡ Unlimited Usage** - No rate limits
- **🏠 Local Processing** - Runs on your machine
- **🎯 High Accuracy** - Excellent semantic search
- **📄 19 Policy Documents** - All indexed and searchable
- **🔍 Smart Search** - Finds relevant policy sections

## 🔧 Technical Details

- **Embedding Model:** `sentence-transformers/all-MiniLM-L6-v2`
- **Dimensions:** 384
- **Vector Database:** Pinecone
- **Document Chunks:** 288 (from 19 PDFs)
- **Chunk Size:** 1000 characters with 200 overlap

## 🛠️ Maintenance

### Add New Documents

1. Place PDFs in `agents/docs/`
2. Run: `python setup_rag.py`

### Update Existing Documents

1. Replace PDFs in `agents/docs/`
2. Run: `python setup_rag.py` (choose to recreate index)

## 🎉 Benefits

| Feature           | Before   | After          |
| ----------------- | -------- | -------------- |
| **Policy Search** | Manual   | **AI-Powered** |
| **Cost**          | N/A      | **FREE**       |
| **Speed**         | Slow     | **Instant**    |
| **Accuracy**      | Variable | **High**       |
| **Coverage**      | Limited  | **Complete**   |

---

**🎊 Your Mira assistant now has enterprise-grade RAG capabilities!**
