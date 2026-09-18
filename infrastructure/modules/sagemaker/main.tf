# ── modules/sagemaker ────────────────────────────────────────────────────────
# Required resources (Task B1). Only these belong in this module:
#
#   aws_sagemaker_domain
#   aws_sagemaker_user_profile
#
# A brand-new AWS account has no service-linked role for Studio, and the
# Domain fails to create with a service-linked role error. Fix it once in the
# console (IAM -> Roles -> Create Role -> AWS Service -> SageMaker -> SageMaker
# Studio) and re-apply. See the New Account Bootstrap note in the lab.
#
# The Domain is also the slowest resource here by a wide margin -- several
# minutes to create and to delete. Factor that into your apply/destroy timings
# for Task B2.

# ── modules/sagemaker ────────────────────────────────────────────────────────
# The Studio Domain and one user profile. In Lab 1 the Domain sits in the
# public subnet with PublicInternetOnly access; Lab 2 moves it to the private
# subnet behind a NAT Gateway, which forces a replacement.
#
# This is the slowest resource in the stack (roughly 8-12 minutes to create,
# similar to delete). A brand-new account also needs the Studio service-linked
# role to exist first; see the New Account Bootstrap note in the lab guide.

resource "aws_sagemaker_domain" "this" {
  domain_name             = "${var.project}-${var.environment}-domain"
  auth_mode               = "IAM"
  vpc_id                  = var.vpc_id
  subnet_ids              = var.subnet_ids
  app_network_access_type = var.app_network_access_type

  default_user_settings {
    execution_role  = var.execution_role_arn
    security_groups = var.security_group_ids

    sharing_settings {
      notebook_output_option = "Disabled"
    }

    jupyter_server_app_settings {
      default_resource_spec {
        instance_type = "system"
      }
    }

    kernel_gateway_app_settings {
      default_resource_spec {
        instance_type = var.instance_type
      }
    }

    # AWS returns this block on every read even when unset; declaring it
    # empty keeps `terraform plan` at "No changes" after the first apply.
    studio_web_portal_settings {}
  }

  # The Domain creates an EFS filesystem for user home directories that
  # Terraform never sees. With the default Retain policy that filesystem, its
  # mount target, and two NFS security groups survive DeleteDomain, the mount
  # target pins the subnet, and `terraform destroy` hangs for 10+ minutes
  # before failing. Delete tells SageMaker to remove the filesystem with the
  # Domain. Lab data never lives in Studio home directories, so nothing of
  # value is lost.

  retention_policy {
    home_efs_file_system = "Delete"
  }

  tags = {
    Name = "${var.project}-${var.environment}-domain"
  }
}

resource "aws_sagemaker_user_profile" "ml_engineer" {
  domain_id         = aws_sagemaker_domain.this.id
  user_profile_name = var.user_profile_name

  user_settings {
    execution_role  = var.execution_role_arn
    security_groups = var.security_group_ids
  }

  tags = {
    Name = "${var.project}-${var.environment}-${var.user_profile_name}"
  }
}
