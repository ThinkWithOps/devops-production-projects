# Remote S3 backend — uncomment after creating the bucket and DynamoDB table
# terraform {
#   backend "s3" {
#     bucket         = "food-delivery-terraform-state"
#     key            = "dev/terraform.tfstate"
#     region         = "us-east-1"
#     encrypt        = true
#     dynamodb_table = "food-delivery-terraform-locks"
#   }
# }

# Local backend (default — no configuration needed)
terraform {
  backend "local" {
    path = "terraform.tfstate"
  }
}
