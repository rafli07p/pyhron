resource "google_sql_database_instance" "pyhron_postgres" {
  name             = "pyhron-postgres-${var.environment}"
  database_version = "POSTGRES_15"
  region           = var.region

  settings {
    tier              = "db-custom-2-7680"
    availability_type = "REGIONAL"

    database_flags {
      name  = "timescaledb.max_background_workers"
      value = "8"
    }

    backup_configuration {
      enabled                        = true
      start_time                     = "02:00"
      point_in_time_recovery_enabled = true
      transaction_log_retention_days = 7

      backup_retention_settings {
        retained_backups = 7
        retention_unit   = "COUNT"
      }
    }

    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.pyhron_vpc.id
    }

    insights_config {
      query_insights_enabled = true
    }
  }

  deletion_protection = true
}

resource "google_sql_database" "pyhron" {
  name     = "pyhron"
  instance = google_sql_database_instance.pyhron_postgres.name
}

resource "google_sql_user" "pyhron" {
  name     = "pyhron"
  instance = google_sql_database_instance.pyhron_postgres.name
  password = "managed-by-secret-manager"
}
