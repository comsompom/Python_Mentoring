# Terraform CI/CD Pipeline Documentation

This document describes the GitHub Actions CI/CD pipeline for automated Terraform infrastructure deployment.

## Overview

The CI/CD pipeline automatically validates, plans, and applies Terraform configurations when changes are pushed or merged to the `main` branch. It supports deployment to multiple cloud providers: **Azure**, **AWS**, and **GCP**.

## Pipeline Workflow

### 1. **Terraform Validation** (Always Runs)
- Validates Terraform syntax and configuration
- Checks code formatting
- Runs on every push and pull request

### 2. **Terraform Plan** (Per Cloud Provider)
- Creates execution plans for each cloud provider
- Runs on pull requests and manual workflow dispatch
- Generates plan artifacts for review

### 3. **Terraform Apply** (Main Branch Only)
- Applies infrastructure changes automatically
- Only runs on `main` branch after successful plan
- Supports manual workflow dispatch for controlled deployments

## Trigger Events

### Automatic Triggers
- **Push to main**: 
  - Always validates and plans for all cloud providers
  - Applies changes **only if** auto-deploy is enabled via secrets (see Auto-Deploy Control Secrets below)
  - By default, auto-deploy is **disabled** for safety
- **Pull Request**: Validates and plans (no apply)

### Manual Trigger (Workflow Dispatch)
You can manually trigger the pipeline with custom parameters:
- **Cloud Provider**: Choose `azure`, `aws`, or `gcp`
- **Environment**: Choose `dev`, `staging`, or `prod`
- **Terraform Action**: Choose `plan`, `apply`, or `destroy`

## Required GitHub Secrets

### Azure Secrets
```
AZURE_CREDENTIALS          # Service principal credentials (JSON)
AZURE_STORAGE_ACCOUNT     # Storage account for Terraform state
AZURE_STORAGE_CONTAINER   # Container name for state files
AZURE_STORAGE_RG          # Resource group for storage account
AZURE_LOCATION            # Default Azure region (optional, defaults to 'eastus')
```

### AWS Secrets
```
AWS_ACCESS_KEY_ID         # AWS access key
AWS_SECRET_ACCESS_KEY     # AWS secret key
AWS_S3_BUCKET            # S3 bucket for Terraform state
AWS_REGION               # AWS region (optional, defaults to 'us-east-1')
```

### GCP Secrets
```
GCP_SA_KEY               # Service account key (JSON)
GCP_PROJECT_ID           # GCP Project ID
GCP_BUCKET_NAME          # GCS bucket for Terraform state
GCP_REGION               # GCP region (optional, defaults to 'us-central1')
```

### Auto-Deploy Control Secrets (Optional)
These secrets control automatic deployment on push to main. Set to `'true'` to enable auto-deploy for each provider. By default, auto-deploy is **disabled** for safety.
```
ENABLE_AUTO_DEPLOY_AZURE  # Set to 'true' to auto-deploy to Azure on main branch push
ENABLE_AUTO_DEPLOY_AWS    # Set to 'true' to auto-deploy to AWS on main branch push
ENABLE_AUTO_DEPLOY_GCP    # Set to 'true' to auto-deploy to GCP on main branch push
```

**Note**: Even if auto-deploy is disabled, you can always deploy manually using the workflow dispatch feature.

## Setting Up GitHub Secrets

1. Go to your GitHub repository
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add each secret with the exact name listed above

### Azure Credentials Setup

For Azure, create a service principal and export as JSON:
```bash
az ad sp create-for-rbac --name "terraform-github-actions" \
  --role contributor \
  --scopes /subscriptions/{subscription-id} \
  --sdk-auth
```

Copy the JSON output and paste it as `AZURE_CREDENTIALS` secret.

### AWS Credentials Setup

1. Create an IAM user with appropriate permissions
2. Attach policies: `AmazonS3FullAccess`, `AmazonEC2FullAccess`, etc.
3. Create access keys and add to secrets

### GCP Credentials Setup

1. Create a service account in GCP
2. Grant necessary roles (Editor, Storage Admin)
3. Create and download JSON key
4. Add JSON content as `GCP_SA_KEY` secret

## Terraform Backend Configuration

The pipeline uses remote backends for state management:

### Azure Backend
- **Storage Account**: Configured via `AZURE_STORAGE_ACCOUNT` secret
- **Container**: Configured via `AZURE_STORAGE_CONTAINER` secret
- **State File**: `terraform.tfstate`

### AWS Backend
- **S3 Bucket**: Configured via `AWS_S3_BUCKET` secret
- **State File**: `terraform.tfstate`
- **Region**: Configured via `AWS_REGION` secret

### GCP Backend
- **GCS Bucket**: Configured via `GCP_BUCKET_NAME` secret
- **State Path**: `terraform/state/terraform.tfstate`

## Environment Protection

The pipeline uses GitHub Environments for deployment protection:
- **dev**: Development environment (less restrictive)
- **staging**: Staging environment (moderate protection)
- **prod**: Production environment (requires approval)

### Setting Up Environment Protection Rules

1. Go to **Settings** → **Environments**
2. Create environments: `dev`, `staging`, `prod`
3. For `prod`, enable:
   - **Required reviewers**: Add team members who must approve
   - **Wait timer**: Optional delay before deployment
   - **Deployment branches**: Restrict to `main` branch only

## Workflow File Location

The workflow file is located at:
```
.github/workflows/terraform-cicd.yml
```

## Terraform Working Directory

All Terraform commands run in:
```
ararchitecture_orion_program/edtech-modernization/
```

## Pipeline Jobs Overview

```
┌─────────────────────┐
│ terraform-validation│
└──────────┬──────────┘
           │
    ┌──────┴──────┬──────────┐
    │             │          │
┌───▼───┐   ┌────▼───┐  ┌───▼────┐
│ Azure │   │  AWS   │  │  GCP   │
│ Plan  │   │ Plan   │  │ Plan   │
└───┬───┘   └────┬───┘  └───┬────┘
    │             │          │
┌───▼───┐   ┌────▼───┐  ┌───▼────┐
│ Azure │   │  AWS   │  │  GCP   │
│ Apply │   │ Apply  │  │ Apply  │
└───────┘   └────────┘  └────────┘
```

## Best Practices

1. **Always Review Plans**: Check plan outputs in pull requests before merging
2. **Use Environments**: Deploy to `dev` first, then `staging`, then `prod`
3. **Monitor Deployments**: Watch workflow runs for any failures
4. **State Management**: Never commit `.tfstate` files (already in `.gitignore`)
5. **Secrets Security**: Rotate secrets regularly and use least-privilege access

## Troubleshooting

### Pipeline Fails at Validation
- Check Terraform syntax: `terraform fmt -check -recursive`
- Validate configuration: `terraform validate`

### Authentication Errors
- Verify secrets are correctly set in GitHub
- Check service principal/IAM user permissions
- Ensure credentials haven't expired

### Backend Configuration Errors
- Verify backend storage resources exist
- Check access permissions for state storage
- Ensure backend configuration matches secrets

### Apply Fails
- Review plan artifacts in workflow runs
- Check cloud provider quotas and limits
- Verify resource naming doesn't conflict

## Manual Workflow Execution

To manually trigger a deployment:

1. Go to **Actions** tab in GitHub
2. Select **Terraform Infrastructure CI/CD** workflow
3. Click **Run workflow**
4. Select:
   - Branch: `main`
   - Cloud Provider: `azure`, `aws`, or `gcp`
   - Environment: `dev`, `staging`, or `prod`
   - Terraform Action: `plan` or `apply`
5. Click **Run workflow**

## Support

For issues or questions:
- Check workflow logs in GitHub Actions
- Review Terraform documentation
- Consult cloud provider documentation

