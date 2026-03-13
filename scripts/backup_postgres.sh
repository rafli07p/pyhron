#!/bin/bash
set -euo pipefail

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BUCKET="gs://pyhron-db-backups"
BACKUP_FILE="pyhron_backup_${TIMESTAMP}.sql.gz"
RETENTION_DAYS=30

echo "Starting backup: $BACKUP_FILE"

pg_dump "$DATABASE_URL" \
  --no-password \
  --verbose \
  --format=custom \
  --compress=9 \
  --file="/tmp/$BACKUP_FILE"

gsutil cp "/tmp/$BACKUP_FILE" "${BUCKET}/daily/${BACKUP_FILE}"
rm "/tmp/$BACKUP_FILE"

echo "Backup uploaded: ${BUCKET}/daily/${BACKUP_FILE}"

# Delete backups older than RETENTION_DAYS
gsutil ls "${BUCKET}/daily/" | while read -r file; do
  file_date=$(echo "$file" | grep -oP '\d{8}')
  if [[ -n "$file_date" ]]; then
    cutoff=$(date -d "-${RETENTION_DAYS} days" +%Y%m%d)
    if [[ "$file_date" < "$cutoff" ]]; then
      gsutil rm "$file"
      echo "Deleted old backup: $file"
    fi
  fi
done

echo "Backup complete"
