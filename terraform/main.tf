provider "google" {
  project = var.project_id
  region  = var.region
}

# Enable the APIs
resource "google_project_service" "bigquery_api" {
  service = "bigquery.googleapis.com"
}
resource "google_project_service" "googleads_api" {
  service = "googleads.googleapis.com"
}
resource "google_project_service" "youtube_api" {
  service = "youtube.googleapis.com"
}
resource "google_project_service" "cloudfunctions_api" {
  service = "cloudfunctions.googleapis.com"
}
resource "google_project_service" "cloudbuild_api" {
  service = "cloudbuild.googleapis.com"
}

# Service account
resource "google_service_account" "service_account" {
  account_id   = "ads-placement-excluder-runner"
  display_name = "Service Account for running Ads Placement Excluder"
}
resource "google_project_iam_member" "sa_cf_role" {
  project = var.project_id
  role    = "roles/cloudfunctions.invoker"
  member  = "serviceAccount:${google_service_account.service_account.email}"
}
resource "google_project_iam_member" "sa_bq_role" {
  project = var.project_id
  role    = "roles/bigquery.admin"
  member  = "serviceAccount:${google_service_account.service_account.email}"
}

# This bucket is used to store the cloud functions for deployment.
# The project ID is used to make sure the name is globally unique
resource "google_storage_bucket" "function_bucket" {
  name                        = "${var.project_id}-functions"
  location                    = var.region
  force_destroy               = true
  uniform_bucket_level_access = true

  lifecycle_rule {
    condition {
      age = 1
    }
    action {
      type = "Delete"
    }
  }
}

data "archive_file" "ads_report_zip" {
  type        = "zip"
  output_path = ".temp/ads_report_code_source.zip"
  source_dir  = "../src/services/gads_reporting/cloud_functions/ads_report/"
}

resource "google_storage_bucket_object" "ads_report" {
  name       = "ads_report_${data.archive_file.ads_report_zip.output_md5}.zip"
  bucket     = google_storage_bucket.function_bucket.name
  source     = data.archive_file.ads_report_zip.output_path
  depends_on = [data.archive_file.ads_report_zip]
}

resource "google_cloudfunctions_function" "ads_report_function" {
  region                = var.region
  name                  = "ads_placement_excluder_ads_report"
  description           = "Move the placement report from Google Ads to BigQuery."
  runtime               = "python310"
  source_archive_bucket = google_storage_bucket.function_bucket.name
  source_archive_object = google_storage_bucket_object.ads_report.name
  service_account_email = google_service_account.service_account.email
  timeout               = 540
  available_memory_mb   = 1024
  entry_point           = "main"
  trigger_http          = true
  depends_on            = [
    google_project_service.cloudfunctions_api,
    google_project_service.cloudbuild_api
  ]

  environment_variables = {
    GOOGLE_ADS_USE_PROTO_PLUS    = false
    GOOGLE_ADS_REFRESH_TOKEN     = var.oauth_refresh_token
    GOOGLE_ADS_CLIENT_ID         = var.google_cloud_client_id
    GOOGLE_ADS_CLIENT_SECRET     = var.google_cloud_client_secret
    GOOGLE_ADS_DEVELOPER_TOKEN   = var.google_ads_developer_token
    GOOGLE_ADS_LOGIN_CUSTOMER_ID = var.google_ads_login_customer_id
    GOOGLE_CLOUD_PROJECT         = var.project_id
  }
}

# BigQuery
resource "google_bigquery_dataset" "dataset" {
  dataset_id                  = "ads_placement_excluder"
  location                    = var.region
  description                 = "Ads Placement Excluder BQ Dataset"
  delete_contents_on_destroy  = true
}
