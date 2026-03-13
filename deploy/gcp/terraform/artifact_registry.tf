resource "google_artifact_registry_repository" "pyhron" {
  location      = var.region
  repository_id = "pyhron"
  format        = "DOCKER"

  cleanup_policies {
    id     = "keep-last-10"
    action = "KEEP"
    most_recent_versions {
      keep_count = 10
    }
  }
}
