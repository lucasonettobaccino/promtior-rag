# Project Overview

## Context

The challenge required building and deploying a RAG-based chatbot capable of
answering questions about Promtior, grounded in the company's website and an
official PDF. Two specific questions had to work end-to-end: _"What services
does Promtior offer?"_ and _"When was the company founded?"_. The stack was
constrained to LangChain + LangServe, and deployment to a major cloud (AWS,
Azure) was expected.

The solution was built with production-grade defaults: observability, reproducible
infrastructure, hardened prompts, and a deterministic retrieval pipeline.

## Approach

Three principles guided the implementation:

**Correctness over cleverness.** The chain is a deterministic LCEL pipeline, not
an agent. For a Q&A system over a fixed corpus, determinism and traceability
outweigh the flexibility of tool-calling agents. This also makes the chain
evaluable in isolation and cheaper to run.

**Engineer the retrieval, then the prompt.** Most RAG failures come from bad
retrieval, not bad prompts. Effort was invested upfront in hybrid retrieval
(BM25 + semantic) followed by a cross-encoder reranker (Cohere), before
spending time tuning the system prompt.

**Treat infrastructure as a first-class citizen.** The solution deploys to AWS
ECS Fargate via Terraform — not Railway — because the goal was to demonstrate
production readiness (VPC, multi-AZ, IaC, Secrets Manager, ALB health checks),
not to ship the fastest path.

## Implementation logic

The end-to-end flow on a question arriving at `/chat/invoke`:

1. **Language analysis.** The question is sent to a lightweight LLM call that
   returns a JSON object with two fields: the detected language (`"English"`,
   `"Spanish"`, etc.) and the question translated to English. This step is the
   foundation for multilingual robustness — the corpus is predominantly
   English-leaning, so retrieval performs better on English queries regardless
   of the user's input language.

2. **Hybrid retrieval.** The English query hits an `EnsembleRetriever` that
   fuses BM25 (lexical) and FAISS (semantic, `text-embedding-3-small`) with
   weights 0.4/0.6, returning the top-10 candidates. The hybrid approach
   handles both exact-keyword matches (company names, dates) and semantic
   variations (paraphrased questions).

3. **Reranking.** The top-10 candidates are reranked by Cohere's
   `rerank-english-v3.0` cross-encoder, reducing to the top-4. This adds
   precision by scoring each chunk against the query in a single forward pass,
   catching cases where dense embeddings rank related-but-wrong chunks
   higher than the actually-relevant one.

4. **Prompt assembly.** The top-4 chunks are concatenated into a context block
   with `[source: ...]` markers. The final prompt includes: the system prompt
   (identity, scope, security boundaries, entity attribution rules with
   few-shot examples), the formatted context, the original question, and
   the detected language as an explicit instruction.

5. **Generation.** `gpt-4o-mini` with `temperature=0` and `max_tokens=1024`
   produces the final answer, grounded in the retrieved context and written
   in the language of the original question.

6. **Response.** Output is parsed into a Pydantic `ChatOutput` schema and
   returned to the client via LangServe's standard endpoints
   (`/chat/invoke`, `/chat/stream`, `/chat/playground/`).

The entire pipeline runs inside two ECS Fargate tasks (ARM64 Graviton) fronted
by an ALB, with secrets injected from AWS Secrets Manager and traces exported
to LangSmith.

## Main challenges & how they were solved

### 1. Entity attribution in coauthored content

The Promtior ebook (`ebook-organizaciones-bionicas`) features a section titled
_"Conocé a los autores"_ that presents biographies of two people: Emiliano
Chinelli (CEO of Promtior) and Ezequiel Kahan (founder of **Knowment**, a
different company). When asked _"Who is the founder of Promtior?"_, the model
initially answered _"Ezequiel Kahan..."_ — conflating a coauthor with a
Promtior team member because both biographies appeared near the word
"Promtior" in the retrieved chunks.

Filtering the page from ingestion would have removed valid context about
Emiliano. Instead, the system prompt was hardened with a rule for entity
attribution — mapping each biographical fact to the specific person and
their specific company, and excluding people not explicitly affiliated
with Promtior. Four few-shot examples were added (founder, universities,
experience, team) demonstrating the correct reasoning on the exact
Promtior/Knowment case. In-context learning with concrete examples proved
significantly more reliable than abstract rules.

Trade-off: the system prompt grew by ~600 tokens per request. Acceptable
given the precision gain on a core failure mode.

### 2. Language-matching inconsistency

Questions in English were occasionally answered in Spanish. `gpt-4o-mini`
with `temperature=0` retains residual non-determinism (GPU
non-determinism on OpenAI's side + token sampling edge cases), and when
the retrieved context leans Spanish, that residual variation was enough
to tip the output language. A simple _"match the user's language"_ rule
in the prompt did not eliminate the issue — it was a reliability
problem, not a comprehension problem.

A lightweight `langdetect`-based detector was tried first. It failed on
short, unaccented Spanish queries like _"Que servicios ofrece Promtior?"_,
which were misclassified as English due to statistical n-gram ambiguity.
The n-gram approach was not robust enough for the query patterns the bot
receives.

The final solution moved language detection into an LLM call at the start
of the chain. The LLM is significantly more robust on short and noisy
input, and its output — the detected language — is passed as an explicit
variable to the main prompt. This replaces a probabilistic model
decision with a deterministic code path: the final LLM no longer infers
the user's language from context, it receives it as an instruction.

Trade-off: an additional LLM call per request, adding ~300-500ms of
latency and a marginal cost increase. Acceptable given that the RAG's
value proposition depends on answering correctly in the user's
language.

### 3. Multilingual retrieval coverage

With language detection fixed, a secondary issue surfaced: Spanish
questions sometimes failed to retrieve the right chunks. The AI_Engineer
PDF contains the founding date in an English passage (_"In May 2023,
Promtior was founded..."_). A Spanish query like _"¿Cuándo fue fundada?"_
produces embeddings biased toward Spanish content, so the BM25 branch
(lexical) found zero matches (no overlap between _"fundada"_ and
_"founded"_), and the semantic branch ranked Spanish chunks higher than
the English PDF chunk that actually held the answer.

The fix reused the LLM language-analysis step from challenge #2. In
addition to detecting the language, the same call also translates the
question to English. The translated query is what the retriever sees;
the original question (with its detected language) is what the final
prompt sees. Result: retrieval always operates in the corpus's dominant
language, while the answer is generated in the user's language.

This turned one LLM call doing two jobs — detection + translation — into
the foundation for both language-matching and multilingual retrieval.

### 4. Wix SPA web scraping

Promtior's website is built on Wix and renders content client-side.
`RecursiveUrlLoader` (the standard LangChain web loader) follows `
href>` tags in the initial HTML response, but Wix's SPA ships only a
shell with navigation built by JavaScript at runtime. The loader found
two pages and stopped.

`SitemapLoader` was used instead, pointing directly at
`https://www.promtior.ai/sitemap.xml`. The sitemap is Wix-generated and
authoritative — it lists every public URL the site wants indexed. After
filtering duplicates, the ingestion pipeline loads 29 pages (~111k
characters) and chunks them into 155 pieces, which combined with the
PDF chunks make up the complete corpus.

Headless browsers (Playwright, Selenium) were considered but rejected
for being overkill when the sitemap is readily available.

## Technologies used

| Layer         | Choice                                        | Reason                                                                                                                 |
| ------------- | --------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| LLM           | OpenAI `gpt-4o-mini`, `temperature=0`         | Cost/quality balance; required by the challenge via OpenAI API.                                                        |
| Embeddings    | OpenAI `text-embedding-3-small`               | Cheap, fast, multilingual.                                                                                             |
| Reranker      | Cohere `rerank-english-v3.0`                  | Cross-encoder precision at low latency.                                                                                |
| Vector store  | FAISS (in-process, persisted)                 | Corpus size (~155 chunks) doesn't justify a dedicated vector DB. Easy to migrate to Qdrant later.                      |
| Framework     | LangChain 1.x + langchain-classic             | Required by the challenge. LCEL for the chain, langchain-classic for the `EnsembleRetriever` and other legacy helpers. |
| API           | LangServe 0.3 on FastAPI                      | Required by the challenge. Ships `/invoke`, `/stream`, `/batch`, and `/playground/` endpoints out of the box.          |
| Config        | Pydantic Settings + SecretStr                 | Type-safe environment config, secrets never logged.                                                                    |
| Logging       | structlog (JSON in prod, console in dev)      | Structured logs work well with CloudWatch Insights.                                                                    |
| Observability | LangSmith                                     | Full chain tracing, including the language-analysis step. Essential for debugging the multilingual issues above.       |
| Container     | Docker multi-stage, ARM64 (Graviton)          | ~20% cheaper than x86 on Fargate with equivalent throughput.                                                           |
| Orchestration | AWS ECS Fargate                               | No EC2 to manage, multi-AZ, ALB integration, rolling deployments via `force-new-deployment`.                           |
| IaC           | Terraform 1.9 + AWS provider ~5.70            | Reproducibility; entire stack destroys/recreates with one command.                                                     |
| Front-end     | Single-file HTML + Tailwind (CDN) + marked.js | A small custom UI with Promtior branding, mounted from `/static`. Parses markdown, renders sources as clickable links. |

## Summary

The system demonstrates that a production-quality RAG can be assembled
without excessive infrastructure or novel components — the difficulty
lies in getting the small decisions right: where to put determinism,
when to trust the LLM vs inject instructions explicitly, and how to
handle real-world content that mixes languages and entities. Each of the
four challenges above took iteration, but each resolution generalized:
the language-analysis pipeline, for example, solved two distinct
problems with a single architectural choice.
