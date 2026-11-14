#!/bin/sh
set -e

# 1) Bring the schema up to date (safe to run on every start).
python manage.py migrate --noinput

# 2) Load the dataset. The command is idempotent: it replaces the table
#    with exactly this dataset, so a fresh database is never left empty.
python manage.py import_insights

# 3) Train the PESTLE model if its artifact is missing. ml/artifacts/ is
#    gitignored and dockerignored, so the blob is always built on first boot.
if [ ! -f ml/artifacts/pestle_pipeline.joblib ]; then
    python manage.py train_model
fi

# Hand off to the image's CMD (Gunicorn).
exec "$@"
