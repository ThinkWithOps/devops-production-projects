variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "environment" {
  description = "Deployment environment"
  type        = string
}

variable "ecr_repository_arns" {
  description = "List of ECR repository ARNs the GitHub Actions user needs access to"
  type        = list(string)
}

variable "eks_cluster_arn" {
  description = "ARN of the EKS cluster"
  type        = string
}
