# Promtior RAG Assistant

Retrieval-augmented chatbot grounded in Promtior's public content (website + onboarding PDF). Built with LangChain + LangServe, deployed to AWS ECS Fargate.

**Live demo:** http://promtior-rag-dev-alb-1271542024.us-east-1.elb.amazonaws.com/

Sample questions the bot answers:

- _What services does Promtior offer?_
- _When was Promtior founded?_
- _Quiénes son los fundadores?_ (the bot replies in the user's language)

## Documentation

- [**Project Overview**](doc/PROJECT_OVERVIEW.md) — approach, implementation logic, challenges encountered, and how they were solved.
- [**Component diagrams**](doc/diagrams/) — request flow (runtime) + ingestion pipeline (offline).

## Architecture at a glance

The system is split into two paths:

- **Ingestion** (offline, pre-deploy): loads the Promtior website via sitemap + the AI_Engineer PDF, chunks documents, builds a FAISS index for semantic search and a BM25 index for lexical search, and persists both to `data/vector_store/`.
- **Runtime** (per-request): the chain analyzes the question's language, translates it to English for retrieval coverage, runs hybrid retrieval (BM25 + FAISS) reranked by Cohere, then generates an answer with gpt-4o-mini grounded in the retrieved context.

See the [component diagrams](doc/diagrams/) for the complete flow.

## Quickstart

### Prerequisites

- Python 3.13+
- [Poetry](https://python-poetry.org/) 2.x
- API keys: OpenAI, Cohere, (optionally) LangSmith

### Setup

```bash
git clone https://github.com/lucasonettobaccino/promtior-rag.git
cd promtior-rag
poetry install
cp .env.example .env
# Edit .env and fill in your API keys
```

### Build the vector store

```bash
poetry run promtior-ingest
```

This loads the PDF and website, chunks them, and persists the indexes under `data/vector_store/`. Takes ~45 seconds (most of it rate-limited sitemap scraping).

### Run the server locally

```bash
poetry run promtior-serve
```

The API is live at http://localhost:8000. Useful endpoints:

- **Chat UI:** http://localhost:8000/
- **Playground:** http://localhost:8000/chat/playground/
- **Health:** http://localhost:8000/healthz
- **OpenAPI:** http://localhost:8000/docs

### Run the tests

```bash
poetry run pytest
```

8 offline tests covering retrieval, language analysis, and prompt rendering. Runs in under a second — no API calls.

## Deployment

The production deployment runs on AWS ECS Fargate, with all infrastructure defined in Terraform under `infra/terraform/`.

```bash
cd infra/terraform
AWS_PROFILE=<your-profile> terraform init
AWS_PROFILE=<your-profile> terraform apply
```

Then push the Docker image to ECR and force a new deployment. See [Project Overview → Known limitations](doc/PROJECT_OVERVIEW.md#known-limitations--roadmap) for the deliberate trade-offs (HTTP-only listener, single NAT gateway, local Terraform state).

## Repository layout

```
promtior-rag/
├── data/
│   ├── AI_Engineer.pdf         # source PDF
│   └── vector_store/           # FAISS + BM25 indexes (built by promtior-ingest)
├── doc/
│   ├── PROJECT_OVERVIEW.md     # approach, challenges, decisions
│   └── diagrams/               # component diagrams (drawio + png)
├── infra/terraform/            # AWS ECS Fargate infrastructure as code
├── src/promtior_rag/
│   ├── api/                    # FastAPI + LangServe server
│   ├── chain/                  # LCEL RAG chain + language analysis + prompts
│   ├── ingestion/              # offline pipeline: loaders, splitter, indexers
│   └── retrieval/              # hybrid retriever + Cohere reranker
├── tests/                      # offline test suite
├── Dockerfile                  # multi-stage ARM64 build for ECS Graviton
└── pyproject.toml              # Poetry config + dependencies + tooling
```

## Tech stack

| Layer         | Stack                                               |
| ------------- | --------------------------------------------------- |
| LLM           | OpenAI gpt-4o-mini (temperature=0)                  |
| Embeddings    | OpenAI text-embedding-3-small                       |
| Reranker      | Cohere rerank-english-v3.0                          |
| Vector store  | FAISS (in-process, persisted) + BM25 (rank-bm25)    |
| Framework     | LangChain 1.x + LangServe 0.3 on FastAPI            |
| Observability | LangSmith (chain tracing) + CloudWatch Logs (infra) |
| Container     | Docker multi-stage, linux/arm64 (Graviton)          |
| Orchestration | AWS ECS Fargate, ALB, Secrets Manager               |
| IaC           | Terraform 1.9                                       |

## License

MIT — see [LICENSE](LICENSE).

## Author

Built by Lucas Onetto Baccino as part of the Promtior technical evaluation.
