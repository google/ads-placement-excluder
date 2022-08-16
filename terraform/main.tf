provider "google" {
  project = var.project_id
  region  = var.region
}

# APIS -------------------------------------------------------------------------
resource "google_project_service" "iam_api" {
  service = "iam.googleapis.com"
}
resource "google_project_service" "cloudresourcemanager_api" {
  service = "cloudresourcemanager.googleapis.com"
}
resource "google_project_service" "serviceusage_api" {
  service = "serviceusage.googleapis.com"
}
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
resource "google_project_service" "sheets_api" {
  service = "sheets.googleapis.com"
}
resource "google_project_service" "cloudscheduler_api" {
  service = "cloudscheduler.googleapis.com"
}
resource "google_project_service" "translate_api" {
  service = "translate.googleapis.com"
}

# SERVICE ACCOUNT --------------------------------------------------------------
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
resource "google_project_iam_member" "sa_ps_role" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.service_account.email}"
}
resource "google_project_iam_member" "sa_sa_role" {
  project = var.project_id
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:${google_service_account.service_account.email}"
}

# CLOUD FUNCTIONS --------------------------------------------------------------
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
data "archive_file" "google_ads_accounts_zip" {
  type        = "zip"
  output_path = ".temp/google_ads_accounts_source.zip"
  source_dir  = "../src/google_ads_accounts"
}
data "archive_file" "google_ads_report_zip" {
  type        = "zip"
  output_path = ".temp/google_ads_report_source.zip"
  source_dir  = "../src/google_ads_report"
}
data "archive_file" "youtube_channel_zip" {
  type        = "zip"
  output_path = ".temp/youtube_channel_source.zip"
  source_dir  = "../src/youtube_channel/"
}
data "archive_file" "google_ads_excluder_zip" {
  type        = "zip"
  output_path = ".temp/google_ads_excluder_source.zip"
  source_dir  = "../src/google_ads_excluder/"
}

resource "google_storage_bucket_object" "google_ads_accounts" {
  name       = "google_ads_accounts_${data.archive_file.google_ads_accounts_zip.output_md5}.zip"
  bucket     = google_storage_bucket.function_bucket.name
  source     = data.archive_file.google_ads_accounts_zip.output_path
  depends_on = [data.archive_file.google_ads_accounts_zip]
}
resource "google_storage_bucket_object" "google_ads_report" {
  name       = "google_ads_report_${data.archive_file.google_ads_report_zip.output_md5}.zip"
  bucket     = google_storage_bucket.function_bucket.name
  source     = data.archive_file.google_ads_report_zip.output_path
  depends_on = [data.archive_file.google_ads_report_zip]
}
resource "google_storage_bucket_object" "youtube_channel" {
  name       = "youtube_channel_${data.archive_file.youtube_channel_zip.output_md5}.zip"
  bucket     = google_storage_bucket.function_bucket.name
  source     = data.archive_file.youtube_channel_zip.output_path
  depends_on = [data.archive_file.youtube_channel_zip]
}
resource "google_storage_bucket_object" "google_ads_excluder" {
  name       = "google_ads_excluder_${data.archive_file.google_ads_excluder_zip.output_md5}.zip"
  bucket     = google_storage_bucket.function_bucket.name
  source     = data.archive_file.google_ads_excluder_zip.output_path
  depends_on = [data.archive_file.google_ads_excluder_zip]
}

resource "google_cloudfunctions_function" "google_ads_accounts_function" {
  region                = var.region
  name                  = "ape-google_ads_accounts"
  description           = "Identify which reports to run the Google Ads report for."
  runtime               = "python310"
  source_archive_bucket = google_storage_bucket.function_bucket.name
  source_archive_object = google_storage_bucket_object.google_ads_accounts.name
  service_account_email = google_service_account.service_account.email
  timeout               = 540
  available_memory_mb   = 1024
  entry_point           = "main"
  trigger_http          = true

  environment_variables = {
    GOOGLE_CLOUD_PROJECT         = var.project_id
    APE_ADS_REPORT_PUBSUB_TOPIC  = google_pubsub_topic.google_ads_report_pubsub_topic.name
  }
}
resource "google_cloudfunctions_function" "google_ads_report_function" {
  region                = var.region
  name                  = "ape-google_ads_report"
  description           = "Move the placement report from Google Ads to BigQuery."
  runtime               = "python310"
  source_archive_bucket = google_storage_bucket.function_bucket.name
  source_archive_object = google_storage_bucket_object.google_ads_report.name
  service_account_email = google_service_account.service_account.email
  timeout               = 540
  available_memory_mb   = 1024
  entry_point           = "main"

  event_trigger {
    event_type = "providers/cloud.pubsub/eventTypes/topic.publish"
    resource   = google_pubsub_topic.google_ads_report_pubsub_topic.name
  }

  environment_variables = {
    GOOGLE_ADS_USE_PROTO_PLUS    = false
    GOOGLE_ADS_REFRESH_TOKEN     = var.oauth_refresh_token
    GOOGLE_ADS_CLIENT_ID         = var.google_cloud_client_id
    GOOGLE_ADS_CLIENT_SECRET     = var.google_cloud_client_secret
    GOOGLE_ADS_DEVELOPER_TOKEN   = var.google_ads_developer_token
    GOOGLE_ADS_LOGIN_CUSTOMER_ID = var.google_ads_login_customer_id
    GOOGLE_CLOUD_PROJECT         = var.project_id
    APE_YOUTUBE_PUBSUB_TOPIC     = google_pubsub_topic.youtube_pubsub_topic.name
  }
}
resource "google_cloudfunctions_function" "youtube_channel_function" {
  region                = var.region
  name                  = "ape-youtube_channel"
  description           = "Pull the channel data from the YouTube API."
  runtime               = "python310"
  source_archive_bucket = google_storage_bucket.function_bucket.name
  source_archive_object = google_storage_bucket_object.youtube_channel.name
  service_account_email = google_service_account.service_account.email
  timeout               = 540
  available_memory_mb   = 1024
  entry_point           = "main"

  event_trigger {
    event_type     = "providers/cloud.pubsub/eventTypes/topic.publish"
    resource       = google_pubsub_topic.youtube_pubsub_topic.name
  }

  environment_variables = {
    GOOGLE_CLOUD_PROJECT          = var.project_id
    APE_ADS_EXCLUDER_PUBSUB_TOPIC = google_pubsub_topic.google_ads_excluder_pubsub_topic.name
  }
}
resource "google_cloudfunctions_function" "google_ads_excluder_function" {
  region                = var.region
  name                  = "ape-google_ads_excluder"
  description           = "Exclude the channels in Google Ads"
  runtime               = "python310"
  source_archive_bucket = google_storage_bucket.function_bucket.name
  source_archive_object = google_storage_bucket_object.google_ads_excluder.name
  service_account_email = google_service_account.service_account.email
  timeout               = 540
  available_memory_mb   = 1024
  entry_point           = "main"

  event_trigger {
    event_type     = "providers/cloud.pubsub/eventTypes/topic.publish"
    resource       = google_pubsub_topic.google_ads_excluder_pubsub_topic.name
  }

  environment_variables = {
    GOOGLE_CLOUD_PROJECT         = var.project_id
    APE_CONFIG_SHEET_ID          = var.config_sheet_id
    GOOGLE_ADS_USE_PROTO_PLUS    = false
    GOOGLE_ADS_REFRESH_TOKEN     = var.oauth_refresh_token
    GOOGLE_ADS_CLIENT_ID         = var.google_cloud_client_id
    GOOGLE_ADS_CLIENT_SECRET     = var.google_cloud_client_secret
    GOOGLE_ADS_DEVELOPER_TOKEN   = var.google_ads_developer_token
    GOOGLE_ADS_LOGIN_CUSTOMER_ID = var.google_ads_login_customer_id
  }
}

# BIGQUERY ---------------------------------------------------------------------
resource "google_bigquery_dataset" "dataset" {
  dataset_id                  = "ads_placement_excluder"
  location                    = var.region
  description                 = "Ads Placement Excluder BQ Dataset"
  delete_contents_on_destroy  = true
}

# PUB/SUB ----------------------------------------------------------------------
resource "google_pubsub_topic" "google_ads_report_pubsub_topic" {
  name                       = "ape-google-ads-report-topic"
  message_retention_duration = "604800s"
}
resource "google_pubsub_topic" "youtube_pubsub_topic" {
  name                       = "ape-youtube-channel-topic"
  message_retention_duration = "604800s"
}
resource "google_pubsub_topic" "google_ads_excluder_pubsub_topic" {
  name                       = "ape-google-ads-excluder-topic"
  message_retention_duration = "604800s"
}

# CLOUD_SCHEDULER --------------------------------------------------------------
locals {
  scheduler_body = <<EOF
    {
        "sheet_id": "${var.config_sheet_id}"
    }
    EOF
}
resource "google_cloud_scheduler_job" "gads_reporting_scheduler" {
  name             = "google_ads_reporting_to_bigquery"
  description      = "Run the export from Google Ads to BigQuery"
  schedule         = "0 8,12,16 * * *"
  time_zone        = "Etc/UTC"
  attempt_deadline = "320s"
  region           = var.region

  http_target {
    http_method = "POST"
    uri         = google_cloudfunctions_function.google_ads_accounts_function.https_trigger_url
    body        = base64encode(local.scheduler_body)
    headers     = {
      "Content-Type" = "application/json"
    }
    oidc_token {
      service_account_email = google_service_account.service_account.email
    }
  }
}
