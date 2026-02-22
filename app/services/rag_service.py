"""
RAG Service — Meeting Knowledge Base.
Uses LangChain + ChromaDB + Gemini for retrieval-augmented Q&A
over meeting transcripts.
"""
import os
import json
import logging
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

STORAGE_DIR = Path("storage")
CHROMA_DIR = STORAGE_DIR / "chroma_db"


class MeetingRAGService:
    """
    Ingest meeting transcripts into ChromaDB and answer questions
    using LangChain ConversationalRetrievalChain + Gemini.
    """

    def __init__(self):
        from langchain_huggingface import HuggingFaceEmbeddings
        from langchain_chroma import Chroma

        self._api_key = os.getenv("GEMINI_API_KEY")
        if not self._api_key:
            raise ValueError("GEMINI_API_KEY not found in .env")

        # Embedding model (small, fast, runs on CPU)
        logger.info("Loading embedding model...")
        self._embeddings = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2",
            model_kwargs={"device": "cpu"},
        )

        # Persistent ChromaDB vector store
        self._vectorstore = Chroma(
            collection_name="meetings",
            embedding_function=self._embeddings,
            persist_directory=str(CHROMA_DIR),
        )
        logger.info("MeetingRAGService initialized (chroma_dir=%s)", CHROMA_DIR)

        # Conversation memories keyed by session_id
        self._memories: dict = {}

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------
    def ingest_meeting(self, meeting_id: str) -> int:
        """
        Load a meeting transcript, chunk by speaker segment, and
        upsert into ChromaDB. Returns the number of chunks indexed.
        """
        from langchain_core.documents import Document

        transcript_path = STORAGE_DIR / meeting_id / "transcript.json"
        if not transcript_path.exists():
            raise FileNotFoundError(
                f"Transcript not found for meeting {meeting_id}"
            )

        with open(transcript_path, "r", encoding="utf-8") as f:
            transcript = json.load(f)

        # Load speaker map
        speaker_map = {}
        map_path = STORAGE_DIR / meeting_id / "speaker_map.json"
        if map_path.exists():
            with open(map_path, "r", encoding="utf-8") as f:
                speaker_map = json.load(f)

        segments = transcript.get("segments", [])
        if not segments:
            logger.warning("[%s] No segments to index", meeting_id)
            return 0

        # Remove old documents for this meeting (re-index)
        self._delete_meeting_docs(meeting_id)

        # Create LangChain Documents — one per segment
        docs = []
        for i, seg in enumerate(segments):
            raw_speaker = seg.get("speaker", "UNKNOWN")
            speaker = speaker_map.get(raw_speaker, raw_speaker)
            text = seg.get("text", "").strip()
            start = seg.get("start", 0.0)
            end = seg.get("end", 0.0)

            if not text:
                continue

            doc = Document(
                page_content=f"{speaker}: {text}",
                metadata={
                    "meeting_id": meeting_id,
                    "speaker": speaker,
                    "speaker_id": raw_speaker,
                    "start": start,
                    "end": end,
                    "chunk_index": i,
                },
            )
            docs.append(doc)

        # Add to ChromaDB
        if docs:
            ids = [f"{meeting_id}_seg_{i}" for i in range(len(docs))]
            self._vectorstore.add_documents(docs, ids=ids)
            logger.info(
                "[%s] Indexed %d segments into ChromaDB", meeting_id, len(docs)
            )

        return len(docs)

    def _delete_meeting_docs(self, meeting_id: str):
        """Remove all existing documents for a meeting from ChromaDB."""
        try:
            collection = self._vectorstore._collection
            existing = collection.get(where={"meeting_id": meeting_id})
            if existing and existing["ids"]:
                collection.delete(ids=existing["ids"])
                logger.info(
                    "[%s] Deleted %d old chunks",
                    meeting_id,
                    len(existing["ids"]),
                )
        except Exception as e:
            logger.warning("Failed to delete old docs: %s", e)

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------
    def query(
        self,
        question: str,
        session_id: str = "default",
        meeting_ids: Optional[list] = None,
    ) -> dict:
        """
        Answer a question using meeting transcripts.

        Returns:
            dict with keys: "answer", "citations"
            Each citation: {meeting_id, speaker, start, end, excerpt}
        """
        from langchain_google_genai import ChatGoogleGenerativeAI
        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

        # Build retriever (with optional meeting filter)
        search_kwargs = {"k": 10}
        if meeting_ids:
            search_kwargs["filter"] = {
                "meeting_id": {"$in": meeting_ids}
            }

        retriever = self._vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs=search_kwargs,
        )

        # Retrieve relevant documents
        docs = retriever.invoke(question)

        # Build context from retrieved documents
        context_parts = []
        for doc in docs:
            meta = doc.metadata
            speaker = meta.get("speaker", "UNKNOWN")
            start = meta.get("start", 0.0)
            mid = meta.get("meeting_id", "unknown")[:8]
            context_parts.append(
                f"[Meeting {mid}, {speaker}, {start:.1f}s]: {doc.page_content}"
            )
        context = "\n".join(context_parts)

        # Build chat history from memory
        history = self._memories.get(session_id, [])
        history_text = ""
        if history:
            hist_lines = []
            for msg in history[-10:]:  # Last 5 exchanges
                hist_lines.append(f"{msg['role'].upper()}: {msg['content']}")
            history_text = "\n".join(hist_lines)

        # System prompt
        system_prompt = """You are ContextIQ, an intelligent meeting assistant. You answer questions ONLY using the meeting transcript excerpts provided below.

RULES:
1. Answer ONLY from the provided context. Never make up information.
2. If the answer is not in the context, say: "I don't have that information in the meetings I've indexed."
3. Always cite the speaker name and approximate timestamp for each fact.
4. Be concise but thorough.
5. Use the speaker's mapped name (not SPEAKER_XX IDs)."""

        # Build messages
        messages = [SystemMessage(content=system_prompt)]

        if history_text:
            messages.append(HumanMessage(
                content=f"Previous conversation:\n{history_text}"
            ))

        user_content = f"MEETING EXCERPTS:\n{context}\n\nQUESTION: {question}"
        messages.append(HumanMessage(content=user_content))

        # Call LLM
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=self._api_key,
            temperature=0.3,
        )
        response = llm.invoke(messages)
        answer = response.content

        # Update conversation memory
        if session_id not in self._memories:
            self._memories[session_id] = []
        self._memories[session_id].append({"role": "user", "content": question})
        self._memories[session_id].append({"role": "assistant", "content": answer})
        # Keep only last 10 messages
        self._memories[session_id] = self._memories[session_id][-10:]

        # Extract citations from source documents
        citations = []
        seen = set()
        for doc in docs:
            meta = doc.metadata
            key = (meta.get("meeting_id"), meta.get("start"))
            if key in seen:
                continue
            seen.add(key)
            citations.append({
                "meeting_id": meta.get("meeting_id", ""),
                "speaker": meta.get("speaker", "UNKNOWN"),
                "start": meta.get("start", 0.0),
                "end": meta.get("end", 0.0),
                "excerpt": doc.page_content[:200],
            })

        return {
            "answer": answer,
            "citations": citations[:5],  # Top 5 sources
        }

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------
    def list_indexed_meetings(self) -> list:
        """Return list of meeting IDs that have been indexed."""
        try:
            collection = self._vectorstore._collection
            result = collection.get(include=["metadatas"])
            meeting_ids = set()
            for meta in result.get("metadatas", []):
                if meta and "meeting_id" in meta:
                    meeting_ids.add(meta["meeting_id"])
            return sorted(meeting_ids)
        except Exception as e:
            logger.warning("Failed to list indexed meetings: %s", e)
            return []

    def clear_chat_history(self, session_id: str = "default"):
        """Clear conversation memory for a session."""
        if session_id in self._memories:
            del self._memories[session_id]
            logger.info("Cleared chat history for session: %s", session_id)

    def get_meeting_chunk_count(self, meeting_id: str) -> int:
        """Return number of indexed chunks for a meeting."""
        try:
            collection = self._vectorstore._collection
            result = collection.get(where={"meeting_id": meeting_id})
            return len(result.get("ids", []))
        except Exception:
            return 0
