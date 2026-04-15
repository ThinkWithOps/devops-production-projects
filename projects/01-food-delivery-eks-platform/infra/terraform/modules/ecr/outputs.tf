output "repository_urls" {
  description = "Map of repository name to URL"
  value       = { for name, repo in aws_ecr_repository.services : name => repo.repository_url }
}

output "repository_arns" {
  description = "Map of repository name to ARN"
  value       = { for name, repo in aws_ecr_repository.services : name => repo.arn }
}

output "registry_id" {
  description = "The registry ID (AWS account ID)"
  value       = values(aws_ecr_repository.services)[0].registry_id
}
