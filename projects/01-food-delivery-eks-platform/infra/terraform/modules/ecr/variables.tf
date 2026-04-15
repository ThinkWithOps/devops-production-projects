variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "environment" {
  description = "Deployment environment"
  type        = string
}

variable "repository_names" {
  description = "List of ECR repository names to create"
  type        = list(string)
  default = [
    "food-delivery/user-service",
    "food-delivery/restaurant-service",
    "food-delivery/order-service",
    "food-delivery/delivery-service"
  ]
}

variable "max_image_count" {
  description = "Maximum number of images to keep per repository"
  type        = number
  default     = 10
}
