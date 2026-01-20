# ============================================================================
# EDP-IO - Production Environment Variables
# ============================================================================
# Use: terraform plan -var-file="environments/prod.tfvars"
#
# IMPORTANT: Production deployments should:
# - Use Azure DevOps or GitHub Actions for CI/CD
# - Require approval gates before apply
# - Have proper RBAC for who can run terraform apply
# ============================================================================

environment  = "prod"
location     = "brazilsouth"
project_name = "edp-io"
owner_email  = "dataplatform@enterprise.com"
cost_center  = "data-engineering"
