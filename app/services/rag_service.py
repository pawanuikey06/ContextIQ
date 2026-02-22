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

        self._api_key = os.getenv("OPENROUTER_API_KEY")
        if not self._api_key:
            raise ValueError("OPENROUTER_API_KEY not found in .env")

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

        # Load meeting metadata (date/day info)
        meeting_meta = {}
        meta_path = STORAGE_DIR / meeting_id / "metadata.json"
        if meta_path.exists():
            with open(meta_path, "r", encoding="utf-8") as f:
                meeting_meta = json.load(f)
        meeting_date = meeting_meta.get("processed_date", "Unknown date")
        meeting_day = meeting_meta.get("processed_day", "Unknown day")

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
                page_content=f"[{meeting_date}, {meeting_day}] {speaker}: {text}",
                metadata={
                    "meeting_id": meeting_id,
                    "speaker": speaker,
                    "speaker_id": raw_speaker,
                    "start": start,
                    "end": end,
                    "chunk_index": i,
                    "meeting_date": meeting_date,
                    "meeting_day": meeting_day,
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
        from langchain_openai import ChatOpenAI
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

        # Build context from retrieved documents (clean, no raw timestamps)
        context_parts = []
        for doc in docs:
            context_parts.append(doc.page_content)
        context = "\n".join(context_parts)

        # Build meeting calendar — list of ALL indexed meetings with dates
        # This enables date-based queries like "what did we discuss on Monday"
        calendar_lines = []
        try:
            for mid in self.list_indexed_meetings():
                meta_path = STORAGE_DIR / mid / "metadata.json"
                if meta_path.exists():
                    with open(meta_path, "r", encoding="utf-8") as f:
                        mm = json.load(f)
                    calendar_lines.append(
                        f"- Meeting {mid[:8]}: {mm.get('processed_date', 'Unknown')}, "
                        f"{mm.get('processed_day', 'Unknown')}, "
                        f"{mm.get('processed_time', '')}"
                    )
        except Exception:
            pass
        meeting_calendar = "\n".join(calendar_lines) if calendar_lines else "No meetings indexed."

        # Build chat history from memory
        history = self._memories.get(session_id, [])
        history_text = ""
        if history:
            hist_lines = []
            for msg in history[-10:]:  # Last 5 exchanges
                hist_lines.append(f"{msg['role'].upper()}: {msg['content']}")
            history_text = "\n".join(hist_lines)

        # System prompt — clean answers, no inline citations
        system_prompt = f"""You are ContextIQ, an intelligent meeting assistant. You answer questions ONLY using the meeting transcript excerpts provided below.

INDEXED MEETINGS:
{meeting_calendar}

RULES:
1. Answer ONLY from the provided context. Never make up information.
2. If the answer is not in the context, say: "I don't have that information in the meetings I've indexed."
3. Give clean, natural answers. Do NOT include timestamps, speaker names in parentheses, or source references in your response. The UI shows sources separately.
4. Be concise but thorough.
5. When asked about dates or days (e.g. "what did we discuss on Monday"), use the INDEXED MEETINGS list above to identify which meetings match, then answer from their content.
6. The date shown in brackets at the start of each excerpt tells you when that meeting happened."""

        # Build messages
        messages = [SystemMessage(content=system_prompt)]

        if history_text:
            messages.append(HumanMessage(
                content=f"Previous conversation:\n{history_text}"
            ))

        user_content = f"MEETING EXCERPTS:\n{context}\n\nQUESTION: {question}"
        messages.append(HumanMessage(content=user_content))

        # Call LLM via OpenRouter
        llm = ChatOpenAI(
            model="google/gemini-2.0-flash-001",
            openai_api_key=self._api_key,
            openai_api_base="https://openrouter.ai/api/v1",
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
