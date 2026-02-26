"""
RAG Service — Meeting Knowledge Base.
Uses LangChain + ChromaDB + Groq (Llama 3.3 70B) for retrieval-augmented
Q&A over meeting transcripts.
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
    using LangChain + Groq (Llama 3.3 70B).
    """

    def __init__(self):
        from langchain_huggingface import HuggingFaceEmbeddings
        from langchain_chroma import Chroma

        self._api_key = os.getenv("GROQ_API_KEY")
        if not self._api_key:
            raise ValueError("GROQ_API_KEY not found in .env")

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
        meeting_title = meeting_meta.get("auto_title", meeting_meta.get("title", f"Meeting {meeting_id[:8]}"))

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
                    "meeting_title": meeting_title,
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
    # Diverse Retrieval — ensures chunks from ALL meetings
    # ------------------------------------------------------------------
    def _diverse_retrieve(self, question: str, meeting_ids=None, target_k=12, fetch_k=25):
        """
        Retrieve chunks across ALL indexed meetings.
        Fetches fetch_k candidates, groups by meeting, then round-robins
        so every meeting is represented in the context.
        Auto-recovers from corrupted ChromaDB by re-indexing.
        """
        from collections import defaultdict

        search_kwargs = {"k": fetch_k}
        if meeting_ids:
            search_kwargs["filter"] = {"meeting_id": {"$in": meeting_ids}}

        retriever = self._vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs=search_kwargs,
        )

        try:
            all_docs = retriever.invoke(question)
        except Exception as e:
            if "Error finding id" in str(e) or "InvalidDimensionException" in str(e):
                logger.warning("ChromaDB index corrupted, rebuilding: %s", e)
                self._rebuild_index()
                # Retry after rebuild
                retriever = self._vectorstore.as_retriever(
                    search_type="similarity",
                    search_kwargs=search_kwargs,
                )
                all_docs = retriever.invoke(question)
            else:
                raise

        # Group by meeting
        by_meeting = defaultdict(list)
        for doc in all_docs:
            mid = doc.metadata.get("meeting_id", "unknown")
            by_meeting[mid].append(doc)

        # Round-robin across meetings
        diverse = []
        meeting_keys = list(by_meeting.keys())
        idx = 0
        while len(diverse) < target_k and meeting_keys:
            key = meeting_keys[idx % len(meeting_keys)]
            if by_meeting[key]:
                diverse.append(by_meeting[key].pop(0))
            else:
                meeting_keys.remove(key)
                if not meeting_keys:
                    break
                continue
            idx += 1

        return diverse

    def _rebuild_index(self):
        """Nuke the ChromaDB collection and re-index all meetings."""
        import shutil
        from langchain_chroma import Chroma

        logger.info("Rebuilding ChromaDB index from scratch...")
        # Delete ChromaDB directory
        if CHROMA_DIR.exists():
            shutil.rmtree(CHROMA_DIR, ignore_errors=True)

        # Recreate vectorstore
        self._vectorstore = Chroma(
            collection_name="meetings",
            embedding_function=self._embeddings,
            persist_directory=str(CHROMA_DIR),
        )

        # Re-index all meetings that have transcripts
        count = 0
        for meeting_dir in STORAGE_DIR.iterdir():
            if not meeting_dir.is_dir() or meeting_dir.name.startswith(".") or meeting_dir.name == "chroma_db":
                continue
            transcript = meeting_dir / "transcript.json"
            if transcript.exists():
                try:
                    n = self.ingest_meeting(meeting_dir.name)
                    count += n
                    logger.info("Re-indexed %s (%d segments)", meeting_dir.name, n)
                except Exception as ex:
                    logger.error("Failed to re-index %s: %s", meeting_dir.name, ex)

        logger.info("Rebuild complete: %d total segments indexed", count)


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
        Uses diverse retrieval to include context from ALL meetings.
        """
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

        # Diverse retrieval across all meetings
        docs = self._diverse_retrieve(question, meeting_ids)

        # Build context
        context = "\n".join(doc.page_content for doc in docs)

        # Build meeting calendar — list of ALL indexed meetings with dates
        # This enables date-based queries like "what did we discuss on Monday"
        calendar_lines = []
        try:
            for m in self.list_indexed_meetings():
                mid = m["id"]
                title = m["title"]
                meta_path = STORAGE_DIR / mid / "metadata.json"
                if meta_path.exists():
                    with open(meta_path, "r", encoding="utf-8") as f:
                        mm = json.load(f)
                    calendar_lines.append(
                        f"- {title}: {mm.get('processed_date', 'Unknown')}, "
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

        # Call LLM via Groq
        llm = ChatOpenAI(
            model="llama-3.3-70b-versatile",
            openai_api_key=self._api_key,
            openai_api_base="https://api.groq.com/openai/v1",
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
        """Return list of {id, title} dicts for all indexed meetings."""
        try:
            collection = self._vectorstore._collection
            result = collection.get(include=["metadatas"])
            seen = {}
            for meta in result.get("metadatas", []):
                if meta and "meeting_id" in meta:
                    mid = meta["meeting_id"]
                    if mid not in seen:
                        seen[mid] = meta.get("meeting_title", f"Meeting {mid[:8]}")
            return [{ "id": mid, "title": title } for mid, title in sorted(seen.items())]
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

    # ------------------------------------------------------------------
    # Streaming Query
    # ------------------------------------------------------------------
    def query_stream(
        self,
        question: str,
        session_id: str = "default",
        meeting_ids: list = None,
    ):
        """
        Stream answer tokens for a question using meeting transcripts.
        Yields (type, data) tuples:
          ("token", "word...")  — streamed answer tokens
          ("citations", [...]) — source citations at the end
          ("done", "")         — signals completion
        """
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage, SystemMessage

        # Diverse retrieval across all meetings
        docs = self._diverse_retrieve(question, meeting_ids)

        # Build context
        context = "\n".join(doc.page_content for doc in docs)

        # Build meeting calendar
        calendar_lines = []
        try:
            for m in self.list_indexed_meetings():
                mid = m["id"]
                title = m["title"]
                meta_path = STORAGE_DIR / mid / "metadata.json"
                if meta_path.exists():
                    with open(meta_path, "r", encoding="utf-8") as f:
                        mm = json.load(f)
                    calendar_lines.append(
                        f"- {title}: {mm.get('processed_date', 'Unknown')}, "
                        f"{mm.get('processed_day', 'Unknown')}, "
                        f"{mm.get('processed_time', '')}"
                    )
        except Exception:
            pass
        meeting_calendar = "\n".join(calendar_lines) if calendar_lines else "No meetings indexed."

        # Chat history
        history = self._memories.get(session_id, [])
        history_text = ""
        if history:
            hist_lines = [f"{msg['role'].upper()}: {msg['content']}" for msg in history[-10:]]
            history_text = "\n".join(hist_lines)

        # System prompt
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
            messages.append(HumanMessage(content=f"Previous conversation:\n{history_text}"))
        messages.append(HumanMessage(content=f"MEETING EXCERPTS:\n{context}\n\nQUESTION: {question}"))

        # Call LLM via Groq with streaming
        llm = ChatOpenAI(
            model="llama-3.3-70b-versatile",
            openai_api_key=self._api_key,
            openai_api_base="https://api.groq.com/openai/v1",
            temperature=0.3,
            streaming=True,
        )

        # Stream tokens
        full_answer = []
        for chunk in llm.stream(messages):
            token = chunk.content
            if token:
                full_answer.append(token)
                yield ("token", token)

        answer = "".join(full_answer)

        # Update memory
        if session_id not in self._memories:
            self._memories[session_id] = []
        self._memories[session_id].append({"role": "user", "content": question})
        self._memories[session_id].append({"role": "assistant", "content": answer})
        self._memories[session_id] = self._memories[session_id][-10:]

        # Extract citations
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

        yield ("citations", citations[:5])
        yield ("done", "")

