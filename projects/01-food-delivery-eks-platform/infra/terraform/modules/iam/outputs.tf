output "github_actions_user_arn" {
  description = "ARN of the GitHub Actions IAM user"
  value       = aws_iam_user.github_actions.arn
}

output "access_key_id" {
  description = "Access key ID for GitHub Actions (add to GitHub secrets as AWS_ACCESS_KEY_ID)"
  value       = aws_iam_access_key.github_actions.id
  sensitive   = true
}

output "secret_access_key" {
  description = "Secret access key for GitHub Actions (add to GitHub secrets as AWS_SECRET_ACCESS_KEY)"
  value       = aws_iam_access_key.github_actions.secret
  sensitive   = true
}
