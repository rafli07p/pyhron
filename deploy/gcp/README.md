# Pyhron GCP Deployment

## Prerequisites

- Google Cloud SDK (`gcloud`) installed and configured
- Terraform >= 1.5
- Docker
- GCP project with billing enabled

## Infrastructure Components

| Component | GCP Service | Purpose |
|-----------|------------|---------|
| Database | Cloud SQL (PostgreSQL 15 + TimescaleDB) | Primary data store |
| Cache | Memorystore (Redis 7.0) | Session cache, rate limiting |
| Streaming | Confluent Cloud on GCP | Event streaming |
| API | Cloud Run | Stateless API service |
| Workers | Cloud Run Jobs | Celery workers |
| Registry | Artifact Registry | Docker images |
| Secrets | Secret Manager | Credentials |
| Monitoring | Cloud Monitoring + Prometheus | Alerting |

## Deployment Steps

### 1. Initialize Terraform State Bucket

```bash
gsutil mb -l asia-southeast2 gs://pyhron-terraform-state
gsutil versioning set on gs://pyhron-terraform-state
```

### 2. Configure Variables

```bash
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your project settings
```

### 3. Apply Infrastructure

```bash
cd deploy/gcp/terraform
terraform init
terraform plan -out=plan.tfplan
terraform apply plan.tfplan
```

### 4. Populate Secrets

```bash
echo -n "postgresql+asyncpg://..." | \
  gcloud secrets versions add pyhron-database_url --data-file=-
```

### 5. Deploy Application

Deployment is automated via CI/CD pipeline:
- Push to `main` deploys to staging
- Git tags (`v*`) deploy to production

### Region: asia-southeast2 (Jakarta)

Chosen for lowest latency to IDX (Indonesia Stock Exchange).
