# ContextIQ: Your Intelligent Meeting Companion

**A project report submitted in the fulfillment of the requirement for the award of the degree of Master of Computer Applications (MCA)**

**Submitted by:**
Squad404
Pawan Kumar Uikey
Ashish Jaiswal
Richa Pandey

---

**DECLARATION**

We, Squad404 (Pawan Kumar Uikey, Ashish Jaiswal, Richa Pandey), hereby declare that the work done in the project entitled **ContextIQ: Your Intelligent Meeting Companion** is done on our own.

We confirm that:
- The work contained in this report is original and has been done by us.
- The work has not been submitted to any other institute for any other degree or diploma.
- We have conformed to ethical norms and guidelines while writing the project report.
- Whenever we have used materials such as data, models, figures, and text from other sources, we have given them due credit by citing them in the report and providing their details in the references.

---

## Abstract

ContextIQ is an intelligent meeting companion application designed to streamline and automate the extraction of knowledge from meeting recordings. By leveraging advanced machine learning models and real-time APIs, the application transforms raw video and audio into structured, searchable, and actionable insights. The backend system is developed using FastAPI and Python, managing complex asynchronous tasks like speech-to-text (STT) and large language model (LLM) orchestration. Svelte powers the frontend, ensuring a highly responsive, modern, and user-friendly interface.

The application dynamically generates bilingual summaries (English and Hindi), extracts context-aware action items, and features a Retrieval-Augmented Generation (RAG) chatbot for interactive Q&A over meeting transcripts. While state-of-the-art models handle audio transcription (WhisperX) and text generation (Llama 3.3 via Groq API), our core responsibilities included full-stack web development, system integration, and building the RAG infrastructure using ChromaDB. ContextIQ aims to provide a comprehensive and intuitive platform that eliminates the need for manual note-taking and enhances team productivity.

**Keywords:** Smart Meeting Application, AI Summarization, Speech-to-Text, FastAPI, Svelte, RAG, ChromaDB, ContextIQ.

---

## 1. Introduction

In modern organizational environments, meetings are an essential aspect of collaboration, decision-making, and knowledge sharing. With the surge in virtual and hybrid work models, the volume of recorded meetings has grown exponentially. However, extracting actionable information from these recordings is often complex and time-consuming. Professionals today are overwhelmed by hours of unstructured audio and video, leading to critical decisions and action items being lost or poorly documented.

Moreover, manual note-taking is inherently flawed—it is slow, prone to bias, and frequently misses important context. A slight misunderstanding or missed nuance can affect an entire project's workflow. This calls for an intelligent solution that automates transcription, summarization, and task extraction with high accuracy and low latency.

This project, titled "ContextIQ: Your Intelligent Meeting Companion," was developed to address these challenges. The primary goal is to simplify and automate meeting documentation through a unified platform that leverages modern web technologies and generative AI. ContextIQ acts as an intelligent assistant that helps users at every step of their post-meeting workflow—from transcribing audio with speaker identification to generating bilingual summaries and interactive, citable Q&A via a custom chatbot.

The key feature of ContextIQ is its ability to generate personalized insights based on a combination of highly accurate local transcription and powerful cloud-based LLMs. For example, utilizing the Groq API for rapid inference, the application can instantly draft follow-up emails, highlight key takeaways, and answer specific questions about what a particular speaker explicitly said during the meeting.

To store and manage the wide range of data, we utilized local JSON storage for persistence and ChromaDB, a high-performance vector database, to support efficient semantic search and retrieval of transcript segments. FastAPI was chosen as the backend technology for its high scalability and ability to handle asynchronous tasks effectively. The frontend was developed using Svelte and Tailwind CSS, providing a dynamic and responsive interface that ensures an engaging user experience across all actions.

---

## 2. Project Overview

### 2.1 Background and Motivation

Meetings form the backbone of professional coordination, enabling strategy alignment and team connectivity. However, the process of documenting a meeting—from taking notes to summarizing discussions and assigning action items—is often overwhelming. With vast amounts of spoken information, users find it difficult to make precise and well-informed records efficiently. Traditional meeting tools often provide basic transcription without true understanding or structuring of the dynamic conversations that occur.

The motivation behind ContextIQ stems from the need to create a **smart, user-friendly, and highly responsive meeting companion** that can simplify the documentation process and offer tailored insights based on highly accurate transcription and advanced AI analysis. By incorporating modern web development technologies and scalable design principles, this project aims to deliver a seamless digital experience for all professionals striving for better productivity.

### 2.2 Project Aim

The primary objective of this project is to design and develop a **web-based meeting intelligence platform** that assists users in structuring meeting recordings in a more intelligent and organized way. The application takes video or audio input and generates optimized transcripts, bilingual summaries, and actionable tasks using integrated APIs and local machine learning models.

The project also aims to streamline multiple post-meeting services—like email drafting, semantic search, and interactive conversational querying—into a **single unified interface** that is intuitive, responsive, and aesthetically appealing.

### 2.3 Key Technologies Used

#### 2.3.1 ChromaDB & Vector Embeddings
ChromaDB is utilized as the primary vector database for storing document embeddings generated from meeting transcripts. We use the **all-MiniLM-L6-v2** model (via HuggingFace) to generate 384-dimensional embeddings. Its efficient vector similarity search is crucial for powering the Retrieval-Augmented Generation (RAG) chatbot, allowing the system to quickly retrieve the most relevant transcript segments to answer user queries accurately.

#### 2.3.2 FastAPI (Python Backend)
FastAPI serves as the robust backend engine. It manages 21+ RESTful API endpoints, handles asynchronous file processing (like video-to-audio extraction using FFmpeg), and orchestrates the complex pipeline between local models and third-party APIs. Its event-driven, high-performance architecture supports real-time Server-Sent Events (SSE) for streaming chatbot responses (~500 tokens/sec via Groq).

#### 2.3.3 Dual Frontend Architecture: Svelte & Streamlit
ContextIQ features a unique dual-frontend design:
*   **Svelte + Vite:** A modern, compiler-based reactive web application providing a high-performance user interface with Tailwind CSS styling.
*   **Streamlit:** A premium, dark-themed analytical dashboard (`streamlit_app.py`) optimized for rapid meeting insights, chat interactions, and management.

#### 2.3.4 Multi-Engine Speech-to-Text (STT)
The system supports multiple transcription modes, prioritizing **AssemblyAI** for top-tier accuracy and integrated diarization. It also includes local fallback options using **WhisperX** (via CTranslate2) and **Faster-Whisper**, combined with **pyannote.audio 4.0** for local speaker diarization on NVIDIA GPUs.

#### 2.3.5 Large Language Model (Groq API)
The core intelligence engine uses **Llama 3.3 70B Versatile** hosted on Groq's LPU (Language Processing Unit) infrastructure. This allows for near-instant generation of bilingual summaries (English and Hindi), structured action items, and professional follow-up email drafts.

---

## 3. System Model

### 3.1 Data Flow and Storage Logic
The storage system follows a hybrid, privacy-first design. Persistent metadata, diarized transcripts, and AI-generated insights are stored as structured JSON files within strictly organized directories. For intelligent interaction, ChromaDB indexes these segments for RAG. This ensures that while AI processing uses APIs, the source data remains structured and manageable on the local file system.

### 3.2 Integration Layer (Jira, Email, Teams)
ContextIQ extends beyond analysis into action:
*   **Jira Integration:** Direct pushing of extracted action items to Jira projects via the Atlassian API.
*   **One-Click Publishing:** Automated generation of professional PDFs (via `fpdf2` with Unicode support for Devanagari) distributed via SMTP and Microsoft Teams Webhooks.

### 3.2 Backend Implementation
The backend of ContextIQ is implemented using **FastAPI** in Python. The server handles client requests, interacts with the local file system and ChromaDB to fetch or store data, processes audio files, and acts as the orchestration layer for all AI operations.

Key backend functionalities include:
*   Extracting audio from uploaded video files via FFmpeg.
*   Transcribing audio and identifying speakers using local WhisperX and pyannote models.
*   Generating structured outputs (bilingual summaries, action items) via the Groq API.
*   Serving secure, real-time Server-Sent Events (SSE) endpoints for the streaming RAG chatbot.

### 3.3 Frontend Implementation
The frontend is built using **Svelte**, creating a dynamic, component-driven user interface. It allows users to:
*   Upload video or audio files seamlessly.
*   View generated transcripts in an interactive, color-coded timeline.
*   Review, edit, and approve AI-generated summaries and action items.
*   Engage with the interactive RAG chatbot to query meeting content.
*   Export the finalized meeting intelligence to professional PDF reports.

Svelte components, styled with Tailwind CSS, help organize the user interface into reusable, maintainable elements, ensuring the application remains aesthetically pleasing and highly responsive.

---

## 4. Methodology

The development of ContextIQ followed an agile, feature-driven approach. The project integrates state-of-the-art AI models, high-performance APIs, and modern web technologies to deliver an end-to-end meeting intelligence pipeline.

### Core Architecture Layers:
1.  **Presentation Layer (Frontend):** Developed with Svelte and Tailwind CSS, focusing on a premium, dark-themed, and highly responsive user experience.
2.  **API Layer (Middle Tier):** Built with FastAPI, exposing decoupled RESTful endpoints for individual features (upload, transcribe, summarize, chat).
3.  **Services & AI Layer (Backend Core):** Contains the heavy lifting, executing Python services that interface with local ML libraries (PyTorch, WhisperX) and cloud APIs (Groq).
4.  **Storage Layer:** Manages JSON file persistence and the ChromaDB vector store.

The methodology prioritized modularity, allowing the transcription engine, the summarization engine, and the RAG chatbot to be developed, tested, and optimized independently before final integration into the unified platform.

---

## 5. Implementation Summary

The implementation of ContextIQ successfully realized a complex pipeline:
1.  **Ingestion:** Video files are processed to extract 16kHz mono audio.
2.  **Transcription:** Local GPU-accelerated algorithms convert speech to text and group it by distinct speakers.
3.  **Indexing:** The completed transcript is segmented, embedded, and indexed into ChromaDB.
4.  **Analysis:** The Groq API is called to generate comprehensive structured datasets including action items, decisions, and bilingual summaries.
5.  **Interaction:** Users browse these results via the Svelte frontend and interact with the data through the integrated RAG chatbot.

---

## 6. Conclusion and Future Work

The development of the ContextIQ web application successfully demonstrates how intelligent system design, combined with advanced generative AI and robust local processing, can significantly streamline post-meeting documentation. By integrating rapid APIs and providing a user-centric interface, the system reduces the time spent on manual note-taking, enhances accountability through automated action item tracking, and improves overall team efficiency.

**Future Directions:**
*   **Live Integration:** Integrate directly with platforms like Zoom, Google Meet, or Microsoft Teams for real-time transcription and analysis.
*   **Enhanced Collaborative Editing:** Allow multiple users to edit the generated summaries and action items simultaneously.
*   **Advanced Analytics:** Introduce dashboards to track sentiment analysis and speaker participation metrics over time.
*   **Deeper Jira Integration:** Fully automate the creation and assignment of tickets directly from the extracted action items.

In conclusion, ContextIQ lays a solid foundation for a smart corporate assistant system, with significant room for innovation in real-time communication intelligence and enterprise workflow automation.
