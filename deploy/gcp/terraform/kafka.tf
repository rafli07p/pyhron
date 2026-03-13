# GCP Kafka configuration.
#
# Options:
# 1. Confluent Cloud (recommended for production): managed Kafka,
#    multi-AZ, schema registry, connectors.
# 2. Google Cloud Managed Service for Apache Kafka (preview as of 2024).
# 3. Self-managed Kafka on GCE (least preferred, ops burden).
#
# This Terraform uses Confluent Cloud via the Confluent Terraform provider.
# If using option 2 or 3, replace this file.

terraform {
  required_providers {
    confluent = {
      source  = "confluentinc/confluent"
      version = "~> 1.82"
    }
  }
}

resource "confluent_environment" "pyhron" {
  display_name = "pyhron-${var.environment}"
}

resource "confluent_kafka_cluster" "pyhron" {
  display_name = "pyhron-kafka"
  availability = "SINGLE_ZONE"
  cloud        = "GCP"
  region       = var.region

  basic {}

  environment {
    id = confluent_environment.pyhron.id
  }
}
