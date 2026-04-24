resource "aws_cloudwatch_log_group" "app" {
  name              = "/ecs/${local.name_prefix}"
  retention_in_days = 7

  tags = {
    Name = "${local.name_prefix}-logs"
  }
}

resource "aws_ecs_cluster" "main" {
  name = "${local.name_prefix}-cluster"

  setting {
    name  = "containerInsights"
    value = "disabled"
  }

  tags = {
    Name = "${local.name_prefix}-cluster"
  }
}

# ARM64 Fargate: ~20% cheaper than x86 for equivalent workload.
# 256 CPU / 1GB is the minimum Fargate combination, enough for this RAG.
resource "aws_ecs_task_definition" "app" {
  family                   = "${local.name_prefix}-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "ARM64"
  }

  container_definitions = jsonencode([
    {
      name      = "app"
      image     = "${aws_ecr_repository.app.repository_url}:latest"
      essential = true

      portMappings = [
        {
          containerPort = 8000
          hostPort      = 8000
          protocol      = "tcp"
        }
      ]

      environment = [
        { name = "APP_ENV",                   value = "production" },
        { name = "LOG_LEVEL",                 value = "INFO" },
        { name = "LOG_FORMAT",                value = "json" },
        { name = "LLM_MODEL",                 value = "gpt-4o-mini" },
        { name = "EMBEDDING_MODEL",           value = "text-embedding-3-small" },
        { name = "LLM_TEMPERATURE",           value = "0.0" },
        { name = "LLM_MAX_TOKENS",            value = "1024" },
        { name = "RERANK_MODEL",              value = "rerank-english-v3.0" },
        { name = "RERANK_TOP_N",              value = "4" },
        { name = "LANGSMITH_TRACING",         value = "true" },
        { name = "LANGSMITH_PROJECT",         value = "promtior-rag" },
        { name = "LANGSMITH_ENDPOINT",        value = "https://api.smith.langchain.com" },
        { name = "PROMTIOR_WEB_URL",          value = "https://www.promtior.ai/sitemap.xml" },
        { name = "PROMTIOR_PDF_PATH",         value = "./data/AI_Engineer.pdf" },
        { name = "CHUNK_SIZE",                value = "1000" },
        { name = "CHUNK_OVERLAP",             value = "200" },
        { name = "VECTOR_STORE_PATH",         value = "./data/vector_store" },
        { name = "RETRIEVER_TOP_K",           value = "10" },
        { name = "RETRIEVER_SEMANTIC_WEIGHT", value = "0.6" },
        { name = "SERVER_HOST",               value = "0.0.0.0" },
        { name = "SERVER_PORT",               value = "8000" },
      ]

      secrets = [
        { name = "OPENAI_API_KEY",    valueFrom = aws_secretsmanager_secret.openai.arn },
        { name = "COHERE_API_KEY",    valueFrom = aws_secretsmanager_secret.cohere.arn },
        { name = "LANGSMITH_API_KEY", valueFrom = aws_secretsmanager_secret.langsmith.arn },
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.app.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "curl --fail http://localhost:8000/healthz || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 30
      }
    }
  ])

  tags = {
    Name = "${local.name_prefix}-task"
  }
}

# desired_count=2 runs one task per AZ for HA.
# min_healthy=50 + max=200 allows rolling deployments without downtime.
resource "aws_ecs_service" "app" {
  name            = "${local.name_prefix}-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = 2
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = [for s in aws_subnet.private : s.id]
    security_groups  = [aws_security_group.ecs_task.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.app.arn
    container_name   = "app"
    container_port   = 8000
  }

  deployment_minimum_healthy_percent = 50
  deployment_maximum_percent         = 200

  health_check_grace_period_seconds = 60

  depends_on = [aws_lb_listener.http]

  tags = {
    Name = "${local.name_prefix}-service"
  }
}