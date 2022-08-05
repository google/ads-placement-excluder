variable "project_id" {
  type        = string
  description = "The project ID to deploy the resources to"
}

variable "region" {
  type        = string
  description = "The region to deploy the resources to, e.g. europe-west2"
  default     = "europe-west2"
}

variable "oauth_refresh_token" {
  type        = string
  description = "The OAuth refresh token"
}

variable "google_cloud_client_id" {
  type        = string
  description = "The client ID from Google Cloud"
}

variable "google_cloud_client_secret" {
  type        = string
  description = "The client secret from Google Cloud"
}

variable "google_ads_developer_token" {
  type        = string
  description = "The Google Ads developer token"
}

variable "google_ads_login_customer_id" {
  type        = string
  description = "The Google Ads MCC customer ID with no dashes"
}

variable "config_sheet_id" {
  type        = string
  description = "The Google Sheeet ID containing the config"
}
