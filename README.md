# Intelligent Customer Support Email Triage & Action System

## 1. Introduction

The **Intelligent Customer Support Email Triage & Action System** is a unified, decision-driven support layer designed to transform reactive email handling into a proactive, coordinated workflow. Unlike traditional ticketing systems that focus solely on classification and suggestions, this platform addresses the root cause of support latency: **information gaps in initial customer emails**. By performing multi-dimensional interpretation of incoming messages, the system proactively requests missing details (like invoice numbers or tracking IDs) through context-aware responses, generates structured action plans for agents using RAG-enriched data from attachments, and dynamically manages urgency to ensure no request is neglected. The ultimate objective is to minimize frictional back-and-forth communication, reduce resolution time, and provide a seamless, transparent experience for both customers and support teams.

## 2. Tech Stack

### AI & Reasoning
- **Primary LLM**: Google Gemini (Flash & Pro models via Google AI Studio)
- **Embeddings**: Gemini Text Embedding models (for RAG)
- **Multilingual Support**: Direct native support for Arabic and English

### Backend
- **Framework**: FastAPI (Python 3.13)
- **Database**: Supabase (PostgreSQL)
- **Vector Search**: pgvector
- **Document Processing**: PyMuPDF, pdfplumber, Tesseract OCR

### Frontend
- **Framework**: React (Vite)
- **Language**: TypeScript
- **State Management**: Zustand
- **Styling**: Vanilla CSS

### Infrastructure
- **Containerization**: Docker, Docker Compose
- **Cloud Services**: Supabase (Database, Storage)

## 3. AI Integration & Development Tools

The development of this system was accelerated and optimized using a suite of AI-powered tools across different project phases:

- **Reasoning & Intelligence**: **Google Gemini** (via Google AI Studio) powers the core interpretation engine, context-aware communication, and RAG retrieval.
- **Project Structuring & Documentation**: **ChatGPT (OpenAI)** was used for idea validation, refining the problem statement, and generating structured documentation (`Proposed_Solution.md` and `Technical_Document.md`).
- **Coding Assistance**: **GitHub Copilot** and **OpenAI CodeX** provided real-time implementation support and boilerplate generation.
- **Workflow Orchestration**: **Gemini CLI** was utilized for specialized codebase analysis, automated refactoring, and maintaining architectural consistency during development.

## 4. Basic Installation Guide

### Prerequisites
- Python 3.13+
- Node.js 18+ & npm
- Tesseract OCR (for image processing)
  - **Mac**: `brew install tesseract`
  - **Ubuntu**: `sudo apt install tesseract-ocr`
- A Supabase Project
- A Google Gemini API Key

### 1. Clone the Repository
```bash
git clone https://github.com/faizaan-nasir/CustomerSupportEmailTriage.git
cd CustomerSupportEmailTriage
```

### 2. Setup Backend
```bash
cd apps/backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your SUPABASE and GEMINI credentials
```

### 3. Setup Frontend
```bash
cd ../../apps/frontend
npm install
cp .env.example .env
# Edit .env with your VITE_SUPABASE and VITE_API credentials
```

### 4. Database Setup
Ensure your Supabase database has the required schema applied (tables: `tickets`, `interpretations`, `entities`, `messages`, `attachments`, `agent_actions`) and the `pgvector` extension enabled.

### 5. Running the Application
**Option A: Using Docker (Fastest)**
```bash
# From the root directory
docker-compose up --build
```

**Option B: Manual Startup**
- **Backend**: `uvicorn app.main:app --reload --port 8000` (from `apps/backend`)
- **Frontend**: `npm run dev` (from `apps/frontend`)

## 5. Supabase Relationship Schema

The system uses a highly relational PostgreSQL schema on Supabase to maintain a single source of truth across all pipeline stages. All child tables are linked to the primary `tickets` table, ensuring that interpretation, extraction, and history are perfectly synchronized.

### Entity Relationship Diagram

```mermaid
erDiagram
    tickets ||--o{ messages : "contains"
    tickets ||--o{ interpretations : "analyzed_as"
    tickets ||--o{ entities : "extracted_from"
    tickets ||--o{ attachments : "has"
    tickets ||--o{ agent_actions : "guides"

    tickets {
        uuid id PK
        text thread_id
        text customer_email
        text subject
        text body
        text status
        double urgency_score
        integer interaction_count
        timestamp created_at
        timestamp updated_at
    }

    messages {
        uuid id PK
        uuid ticket_id FK
        text sender
        text content
        timestamp timestamp
    }

    interpretations {
        uuid id PK
        uuid ticket_id FK
        text intent
        text category
        text sentiment
        double urgency
        double confidence
        text reasoning
        jsonb raw_output
        timestamp created_at
    }

    entities {
        uuid id PK
        uuid ticket_id FK
        text key
        text value
        text source
        double confidence
        timestamp created_at
    }

    attachments {
        uuid id PK
        uuid ticket_id FK
        text file_url
        text parsed_text
        vector embedding
        timestamp created_at
    }

    agent_actions {
        uuid id PK
        uuid ticket_id FK
        text summary
        text action_plan
        text escalation_target
        timestamp generated_at
    }
```

### Key Database Features:
- **pgvector**: Enables semantic similarity search across attachments for RAG extraction.
- **Optimized Indexing**: Employs targeted B-tree indexes across critical query paths to ensure low-latency dashboard updates and high-performance triage as the system scales.

## 6. Conclusion

The **Intelligent Customer Support Email Triage & Action System** represents a shift from reactive helpdesk tools to a coordinated, proactive decision system. By leveraging Large Language Models for deep interpretation and RAG for document intelligence, the system successfully bridges the gap between raw customer input and actionable resolution. This architecture not only speeds up response times but also ensures that support operations are consistent, fair, and data-driven.
