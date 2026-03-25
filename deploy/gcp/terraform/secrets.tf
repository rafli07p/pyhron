locals {
  secrets = [
    "database_url",
    "redis_url",
    "jwt_secret",
    "eodhd_api_token",
    "alpaca_api_key",
    "alpaca_api_secret",
  ]
}

resource "google_secret_manager_secret" "pyhron_secrets" {
  for_each  = toset(local.secrets)
  secret_id = "pyhron-${each.key}"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_iam_member" "api_secret_access" {
  for_each  = toset(local.secrets)
  secret_id = google_secret_manager_secret.pyhron_secrets[each.key].secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.pyhron_api.email}"
}

# Grant ingestion service account access to Alpaca secrets
resource "google_secret_manager_secret_iam_member" "ingestion_secret_access" {
  for_each  = toset(["alpaca_api_key", "alpaca_api_secret"])
  secret_id = google_secret_manager_secret.pyhron_secrets[each.key].secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.pyhron_ingestion.email}"
}
