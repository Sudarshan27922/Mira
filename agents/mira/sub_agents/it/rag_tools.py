from typing import Dict, Any

from langchain_core.tools import tool

from agents.mira.rag_tool import get_vector_store_manager


NAMESPACE = "it"
CATEGORY = "it"


@tool
def search_it_knowledge(query: str) -> str:
    """Search the IT knowledge base (namespace 'it') for relevant guidance and FAQs.
    Returns short citations and content snippets."""
    mgr = get_vector_store_manager()
    results = mgr.search_documents(query, k=5, namespace=NAMESPACE, category=CATEGORY)
    if not results:
        return "No relevant IT knowledge found."

    lines = [f"Found {len(results)} IT knowledge snippets:\n"]
    for i, doc in enumerate(results, 1):
        meta: Dict[str, Any] = doc.metadata or {}
        filename = meta.get("filename", "Unknown Document")
        part = meta.get("chunk_index", 0) + 1
        total = meta.get("total_chunks", 1)
        lines.append(f"{i}. {filename} (Part {part} of {total})\n   {doc.page_content}\n")
    return "\n".join(lines)


@tool
def summarize_it_topic(topic: str) -> str:
    """Summarize guidance related to a given IT topic from the IT knowledge base."""
    mgr = get_vector_store_manager()
    results = mgr.search_documents(topic, k=10, namespace=NAMESPACE, category=CATEGORY)
    if not results:
        return f"No IT knowledge found for '{topic}'."

    grouped: Dict[str, list] = {}
    for doc in results:
        filename = (doc.metadata or {}).get("filename", "Unknown")
        grouped.setdefault(filename, []).append(doc)

    out = [f"IT Knowledge Summary for '{topic}':\n"]
    for fname, docs in grouped.items():
        out.append(f"## {fname}\nFound {len(docs)} relevant sections:\n")
        for i, d in enumerate(docs, 1):
            out.append(f"Section {i}:\n{d.page_content}\n")
    return "\n".join(out)


IT_RAG_TOOLS = [search_it_knowledge, summarize_it_topic]


