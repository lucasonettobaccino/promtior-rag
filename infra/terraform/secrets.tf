# Secret values are populated via `aws secretsmanager put-secret-value` after apply,
# so the actual keys never touch terraform state.

resource "aws_secretsmanager_secret" "openai" {
  name                    = "${local.name_prefix}/openai-api-key"
  description             = "OpenAI API key for LLM and embeddings"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret" "cohere" {
  name                    = "${local.name_prefix}/cohere-api-key"
  description             = "Cohere API key for reranker"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret" "langsmith" {
  name                    = "${local.name_prefix}/langsmith-api-key"
  description             = "LangSmith API key for tracing"
  recovery_window_in_days = 0
}