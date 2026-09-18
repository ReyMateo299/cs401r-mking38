output "domain_id" {
  description = "ID of the SageMaker Domain"
  value       = aws_sagemaker_domain.this.id
}

output "user_profile_name" {
  description = "ID of the SageMaker user profile"
  value       = aws_sagemaker_user_profile.ml_engineer.user_profile_name
}

# TODO: Add domain_url ?