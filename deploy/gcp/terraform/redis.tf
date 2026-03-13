resource "google_redis_instance" "pyhron_redis" {
  name           = "pyhron-redis-${var.environment}"
  tier           = "STANDARD_HA"
  memory_size_gb = 1
  region         = var.region
  redis_version  = "REDIS_7_0"

  auth_enabled            = true
  transit_encryption_mode = "SERVER_AUTHENTICATION"

  maintenance_policy {
    weekly_maintenance_window {
      day = "SUNDAY"
      start_time {
        hours   = 2
        minutes = 0
      }
    }
  }
}
