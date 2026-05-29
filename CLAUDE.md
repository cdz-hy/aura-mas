# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AURA (智学) is a multi-agent personalized learning system with three services:
- **Java-backend** — Spring Boot 3.2.5 (Java 17), business logic + data persistence
- **Python-backend** — FastAPI + LangGraph multi-agent AI system
- **Vue-frontend** — Vue 3 + TypeScript + Vite SPA

## Build & Run Commands

### Java Backend (port 8080)
```bash
cd Java-backend
mvn clean package              # Build
mvn spring-boot:run            # Run
mvn test                       # Run all tests
mvn test -Dtest=TaskProducerTest  # Run single test class
```
Requires: Java 17, MySQL, RabbitMQ. Uses `application-local.yml` for local config (gitignored); see `application-example.yml` for template.

### Python Backend (port 8002)
```bash
cd Python-backend
pip install -r requirements.txt
python main.py                 # Run (uvicorn on port 8002)
```
Requires: Python 3.11+, `.env` file (see `.env.template`). No pytest configured; tests in `tests/` are scripts, not unit tests.

### Vue Frontend (port 5173)
```bash
cd Vue-frontend
npm install
npm run dev                    # Dev server with proxy to Java at :8080
npm run build                  # Type-check + production build
```
No test framework configured.

## Architecture

### Service Communication

```
Vue (5173) ──HTTP /api/*──► Java (8080) ──RabbitMQ──► Python (8002)
Vue (5173) ──HTTP /api/ai/*──► Python (8002)  [SSE streaming]
Python (8002) ──HTTP /api/internal/*──► Java (8080)  [persistence]
```

- **Java→Python (async)**: Java produces tasks to RabbitMQ queue `ai.resource.generation` (exchange `ai.exchange`, routing key `ai.resource.generation`). Python MQ consumer runs the LangGraph workflow.
- **Python→Java (sync)**: Python calls Java internal APIs to persist results. Authenticated via `X-Service-Secret` header, bypassing JWT.
- **Frontend→Python (direct)**: Vue calls Python SSE endpoints at `:8002` for AI chat. Auth uses short-lived "ticket" JWTs (5-min expiry) issued by Java.
- **SSE**: Python streams AI responses to frontend; Java pushes task completion notifications via `TaskSseService`.

### Resource Generation Flow
1. Frontend → Java: create plan/resource
2. Java: creates `ResourceGenerationTask` in DB, dispatches to RabbitMQ
3. Python MQ consumer: runs LangGraph graph (`app/graph/learning_graph.py`)
4. Python → Java: persists results via internal HTTP APIs
5. Java → Frontend: SSE push with task completion

### Multi-Agent System (Python)

LangGraph `StateGraph` in `app/graph/learning_graph.py` with 12+ nodes:
- `controller` — intent classification and routing
- `task_decomposer` — breaks learning goals into sub-tasks
- `rag_retriever` — hybrid dense+sparse vector search (Qdrant) with reranking
- `content_orchestrator` — assembles retrieved content
- `reviewer` — quality check with retry logic
- `resource_generator` — autonomous content generation (web search fallback via Tavily)
- `resource_type_generator` — generates mindmap/summary/code resources
- `quiz_generator` / `quiz_grader` — quiz creation and grading
- `profile_maintainer` — updates user learning profile
- `tutor_agent` — module-specific tutoring
- `simple_answer` — straightforward Q&A

LLM tiers (via `app/agents/llm_factory.py`):
- `mimo-v2.5-pro` — most agents (controller, task_decomposer, RAG, reviewer, quiz, profile)
- `mimo-v2.5` — content orchestration
- `mimo-v2-flash` — lightweight tasks
- Qwen models (DashScope) — embeddings and RAG chat

### Hybrid RAG Pipeline (`app/services/retrieval.py`)
- Dense: Qwen3-VL-Embedding (2560-dim)
- Sparse: BM25 via fastembed
- Vector DB: Qdrant with DBSF fusion
- Reranking: Qwen3-VL-Rerank
- Parent chunk retrieval and deduplication

### Auth Model
- Java issues JWT access tokens + refresh tokens
- Short-lived "ticket" JWTs bridge frontend→Python auth
- Internal service calls use `X-Service-Secret` header
- Role-based: admin vs student, dynamic menu/route generation

### Database
- MySQL with MyBatis-Plus ORM
- Schema auto-executed on startup (`schema.sql`, `data.sql`)
- Migrations in `src/main/resources/migration_*.sql`

## Port Map

| Service | Port |
|---------|------|
| Java backend | 8080 |
| Python backend | 8002 |
| Vue dev server | 5173 |
| Qdrant | 6333 |
| RabbitMQ | 5672 |
| MySQL | 3306 |
| MinIO | 9000 |

## External Services

- **MySQL** — primary database
- **RabbitMQ** — task queue between Java and Python
- **Qdrant** — vector database for RAG
- **MinIO** — local object storage
- **Qiniu Cloud OSS** — cloud object storage
- **DashScope** (Alibaba Cloud) — Qwen LLMs, embeddings, reranker
- **MIMO API** (Xiaomi) — primary LLM (OpenAI-compatible)
- **MinerU** — document parsing
- **Tavily** — web search for resource generation

## Code Conventions

### Java Backend
- Package: `com.learning`
- ORM: MyBatis-Plus with XML mappers in `src/main/resources/mapper/`
- Config profiles: `application.yml` (default), `application-local.yml` (local, gitignored)
- Lombok for boilerplate reduction
- SpringDoc OpenAPI for API docs (Swagger UI)

### Python Backend
- Config via Pydantic Settings (`app/core/config.py`) loading from `.env`
- Agent definitions in `app/agents/`, graph in `app/graph/`
- DB operations go through `java_client` singleton (`app/services/db/java_client.py`)
- Async RabbitMQ consumer via `aio-pika`

### Vue Frontend
- TypeScript strict mode
- Tailwind CSS with custom palette (navy, cream, sage) in `tailwind.config.js`
- State management: Pinia stores in `src/stores/`
- API proxy: Vite dev server proxies `/api` to Java backend at `:8080`
- SSE client utility: `src/utils/sse.ts`
