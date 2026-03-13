resource "google_monitoring_alert_policy" "api_error_rate" {
  display_name = "Pyhron API Error Rate"
  combiner     = "OR"

  conditions {
    display_name = "5xx error rate > 5%"
    condition_threshold {
      filter          = "resource.type = \"cloud_run_revision\" AND metric.type = \"run.googleapis.com/request_count\""
      duration        = "120s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0.05
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.name]
  alert_strategy {
    auto_close = "1800s"
  }
}

resource "google_monitoring_alert_policy" "api_latency" {
  display_name = "Pyhron API P95 Latency"
  combiner     = "OR"

  conditions {
    display_name = "P95 latency > 2s"
    condition_threshold {
      filter          = "resource.type = \"cloud_run_revision\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 2000
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.name]
}

resource "google_monitoring_notification_channel" "email" {
  display_name = "Pyhron Alerts Email"
  type         = "email"
  labels = {
    email_address = var.alert_email
  }
}
