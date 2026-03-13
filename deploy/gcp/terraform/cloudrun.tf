resource "google_service_account" "pyhron_api" {
  account_id   = "pyhron-api-sa"
  display_name = "Pyhron API Service Account"
}

resource "google_cloud_run_v2_service" "pyhron_api" {
  name     = "pyhron-api"
  location = var.region

  template {
    service_account = google_service_account.pyhron_api.email

    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/pyhron/api:latest"

      resources {
        limits = {
          cpu    = "2"
          memory = "2Gi"
        }
        startup_cpu_boost = true
      }

      env {
        name  = "ENV"
        value = "production"
      }

      env {
        name = "DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.pyhron_secrets["database_url"].secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "REDIS_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.pyhron_secrets["redis_url"].secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "JWT_SECRET_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.pyhron_secrets["jwt_secret"].secret_id
            version = "latest"
          }
        }
      }

      liveness_probe {
        http_get {
          path = "/health"
        }
        initial_delay_seconds = 10
        period_seconds        = 15
      }

      startup_probe {
        http_get {
          path = "/health"
        }
        failure_threshold = 10
        period_seconds    = 5
      }
    }

    scaling {
      min_instance_count = 1
      max_instance_count = 5
    }

    vpc_access {
      connector = google_vpc_access_connector.pyhron.id
      egress    = "PRIVATE_RANGES_ONLY"
    }
  }
}
