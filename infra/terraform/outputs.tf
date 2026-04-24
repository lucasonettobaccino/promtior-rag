output "ecr_repository_url" {
  description = "ECR repository URL for pushing Docker images."
  value       = aws_ecr_repository.app.repository_url
}

output "ecr_repository_name" {
  description = "ECR repository name."
  value       = aws_ecr_repository.app.name
}

output "alb_dns_name" {
  description = "ALB DNS name - use this to reach the API."
  value       = aws_lb.main.dns_name
}

output "alb_url" {
  description = "Full URL to access the API."
  value       = "http://${aws_lb.main.dns_name}"
}

output "ecs_cluster_name" {
  description = "ECS cluster name - use for awscli commands."
  value       = aws_ecs_cluster.main.name
}

output "ecs_service_name" {
  description = "ECS service name."
  value       = aws_ecs_service.app.name
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group for ECS tasks."
  value       = aws_cloudwatch_log_group.app.name
}