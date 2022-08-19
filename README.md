# Ads Placement Excluder

## Problem

It is manual and challenging to detect YouTube channel placements which might be
spam (low performance with high cost), and exclude them from future advertising.
Google Ads does not currently provide enough granularity to identify all spam
channels.

## Solution

Based on performance, a client can define what their interpretation of a spam
channel is, and our solution will leverage the Google Ads & YouTube APIs to
automate identifying these placements, and exclude them from future advertising.

## Architecture

TODO: write me.

## OAuth

https://www.googleapis.com/auth/spreadsheets.readonly
https://www.googleapis.com/auth/cloud-platform
https://www.googleapis.com/auth/youtube
https://www.googleapis.com/auth/adwords

## Roles
https://cloud.google.com/iam/docs/understanding-roles

## Deployment

TODO: explain
https://medium.com/rockedscience/how-to-fully-automate-the-deployment-of-google-cloud-platform-projects-with-terraform-16c33f1fb31f
```
gcloud services enable serviceusage.googleapis.com cloudresourcemanager.googleapis.com iam.googleapis.com cloudresourcemanager.googleapis.com serviceusage.googleapis.com bigquery.googleapis.com googleads.googleapis.com youtube.googleapis.com cloudfunctions.googleapis.com cloudbuild.googleapis.com sheets.googleapis.com cloudscheduler.googleapis.com translate.googleapis.com
```

The deployment is managed by Terraform, so installation is required before
following these steps ([instructions](https://learn.hashicorp.com/tutorials/terraform/install-cli)).

1. Terraform's state is tracked in Google Cloud storage, so before starting the
   deployment, manually create a cloud storage bucket and make a note of the
   name.
2. Run the following commands:
   ```
   cd terraform
   terraform init
   ```
   When prompted, enter the name of the bucket created in step 1.
3. Create a file named `terraform.tfvars` and add the following variables:
   ```
   project_id = ""
   oauth_refresh_token = ""
   google_cloud_client_id = ""
   google_cloud_client_secret = ""
   google_ads_developer_token = ""
   google_ads_login_customer_id = ""
   config_sheet_id= = ""
   ```
   Note that the `google_ads_login_customer_id` is the MCC customer ID in Google
   Ads.
4. Run `terraform plan` and review the proposed changes.
5. Run `terraform apply` to create the infrastructure.
