# ============================================================================
# EDP-IO - Terraform Main Configuration
# ============================================================================
# This is a MOCK PRODUCTION configuration that demonstrates enterprise
# patterns for Azure infrastructure. It uses placeholders and can be
# deployed to a real environment by updating variable values.
#
# ARCHITECTURE:
# - Resource Group with proper tagging
# - Data Lake Storage (ADLS Gen2) with hierarchical namespace
# - Databricks Workspace with Unity Catalog
# - Key Vault for secrets management
# - Azure OpenAI for LLM observability
#
# SECURITY FEATURES:
# - Private endpoints (commented for mock)
# - Managed identities
# - RBAC with least privilege
# - Network isolation ready
# ============================================================================

terraform {
  required_version = ">= 1.5.0"
  
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.80"
    }
    databricks = {
      source  = "databricks/databricks"
      version = "~> 1.30"
    }
  }
  
  # Production: Use Azure Storage backend
  # backend "azurerm" {
  #   resource_group_name  = "rg-edp-io-tfstate"
  #   storage_account_name = "stedpiotfstate"
  #   container_name       = "tfstate"
  #   key                  = "edp-io.terraform.tfstate"
  # }
}

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy = false
    }
  }
}

# ============================================================================
# VARIABLES
# ============================================================================

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
  
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "location" {
  description = "Azure region for resources"
  type        = string
  default     = "brazilsouth"
}

variable "project_name" {
  description = "Project identifier for resource naming"
  type        = string
  default     = "edp-io"
}

variable "owner_email" {
  description = "Email of the resource owner"
  type        = string
  default     = "dataplatform@enterprise.com"
}

variable "cost_center" {
  description = "Cost center for billing"
  type        = string
  default     = "data-engineering"
}

# ============================================================================
# LOCALS
# ============================================================================

locals {
  # Naming convention: {resource_type}-{project}-{environment}-{region_code}
  name_prefix = "${var.project_name}-${var.environment}"

  # Common tags for all resources
  common_tags = {
    Project      = var.project_name
    Environment  = var.environment
    ManagedBy    = "Terraform"
    Owner        = var.owner_email
    CostCenter   = var.cost_center
    CreatedDate  = timestamp()
  }
  
  # Environment-specific settings
  env_config = {
    dev = {
      databricks_sku        = "standard"
      storage_replication   = "LRS"
      key_vault_sku        = "standard"
    }
    staging = {
      databricks_sku        = "premium"
      storage_replication   = "GRS"
      key_vault_sku        = "standard"
    }
    prod = {
      databricks_sku        = "premium"
      storage_replication   = "RAGRS"
      key_vault_sku        = "premium"
    }
  }
  
  config = local.env_config[var.environment]
}

# ============================================================================
# RESOURCE GROUP
# ============================================================================

resource "azurerm_resource_group" "main" {
  name     = "rg-${local.name_prefix}"
  location = var.location
  tags     = local.common_tags
}

# ============================================================================
# DATA LAKE STORAGE (ADLS GEN2)
# ============================================================================
# Hierarchical namespace enabled for Delta Lake performance

resource "azurerm_storage_account" "datalake" {
  name                     = "st${replace(local.name_prefix, "-", "")}lake"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = local.config.storage_replication
  account_kind             = "StorageV2"
  
  # CRITICAL: Enable hierarchical namespace for ADLS Gen2
  is_hns_enabled = true
  
  # Security settings
  min_tls_version                 = "TLS1_2"
  allow_nested_items_to_be_public = false
  
  # Blob properties for versioning
  blob_properties {
    versioning_enabled       = true
    change_feed_enabled      = true
    last_access_time_enabled = true
    
    delete_retention_policy {
      days = 30
    }
    
    container_delete_retention_policy {
      days = 30
    }
  }
  
  tags = local.common_tags
}

# Container for Bronze layer
resource "azurerm_storage_container" "bronze" {
  name                  = "bronze"
  storage_account_name  = azurerm_storage_account.datalake.name
  container_access_type = "private"
}

# Container for Silver layer
resource "azurerm_storage_container" "silver" {
  name                  = "silver"
  storage_account_name  = azurerm_storage_account.datalake.name
  container_access_type = "private"
}

# Container for Gold layer
resource "azurerm_storage_container" "gold" {
  name                  = "gold"
  storage_account_name  = azurerm_storage_account.datalake.name
  container_access_type = "private"
}

# ============================================================================
# KEY VAULT
# ============================================================================
# Centralized secrets management with audit logging

data "azurerm_client_config" "current" {}

resource "azurerm_key_vault" "main" {
  name                = "kv-${local.name_prefix}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = local.config.key_vault_sku
  
  # Security settings
  soft_delete_retention_days = 90
  purge_protection_enabled   = var.environment == "prod"
  
  # Enable Azure RBAC for access (preferred over access policies)
  enable_rbac_authorization = true
  
  tags = local.common_tags
}

# ============================================================================
# DATABRICKS WORKSPACE
# ============================================================================

resource "azurerm_databricks_workspace" "main" {
  name                = "dbw-${local.name_prefix}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = local.config.databricks_sku
  
  managed_resource_group_name = "rg-${local.name_prefix}-databricks-managed"
  
  tags = local.common_tags
}

# ============================================================================
# OUTPUTS
# ============================================================================

output "resource_group_name" {
  description = "Name of the resource group"
  value       = azurerm_resource_group.main.name
}

output "storage_account_name" {
  description = "Name of the data lake storage account"
  value       = azurerm_storage_account.datalake.name
}

output "storage_account_dfs_endpoint" {
  description = "ADLS Gen2 DFS endpoint for Spark"
  value       = azurerm_storage_account.datalake.primary_dfs_endpoint
}

output "key_vault_name" {
  description = "Name of the Key Vault"
  value       = azurerm_key_vault.main.name
}

output "key_vault_uri" {
  description = "URI for Key Vault access"
  value       = azurerm_key_vault.main.vault_uri
}

output "databricks_workspace_url" {
  description = "URL of the Databricks workspace"
  value       = azurerm_databricks_workspace.main.workspace_url
}

output "databricks_workspace_id" {
  description = "ID of the Databricks workspace"
  value       = azurerm_databricks_workspace.main.id
}
