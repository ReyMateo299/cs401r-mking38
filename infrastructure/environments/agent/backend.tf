# Track C uses a separate state key so it cannot modify the Labs 1–2 stack.
terraform {
  backend "s3" {
    bucket         = "northstar-tfstate-480747229391"
    key            = "agent/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "northstar-tfstate-lock"
    encrypt        = true
  }
}
