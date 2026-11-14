# Enerlytics - Global Energy & Sustainability Intelligence Dashboard

Enerlytics is a **web-based business intelligence dashboard project** that analyzes global energy and environmental insights across sectors, regions, and risk dimensions.

## Project Overview
This project focuses on:
- Energy and environmental trends
- Sector-wise and geographic intelligence
- Risk assessment using intensity and likelihood metrics
- PESTLE-based contextual analysis
- Machine learning: automatic PESTLE classification of insight titles

The dashboard is designed as a **single-page BI view** with logical sections for fast insight consumption. All filtering, KPI recalculation, and chart re-rendering happen without a full page reload.

## Tools & Technologies

- **Backend:** Django (Python 3.14+)
- **Frontend:** Django Templates + HTMX (partial page swaps, no SPA framework)
- **Charts & Visualizations:** Chart.js
- **Database:** PostgreSQL 17 with pgvector (via Docker), with automatic SQLite fallback for local runs
- **Data Loading:** Django management command (`import_insights`) that cleans and loads `data/jsondata.json`
- **Styling / Performance:** WhiteNoise for static files, Gunicorn as the production server
- **Machine Learning:** scikit-learn (LinearSVC + TF-IDF), pandas, joblib
- **Testing:** pytest + pytest-django
- **Deployment:** Docker & docker-compose

## Getting Started

### Option 1: Docker (recommended)
```bash
cp .env.example .env    # fill in Postgres credentials
docker compose up --build
```
The app runs at http://localhost:8000 and connects to the bundled `pgvector/pgvector:pg17` database service automatically. The container entrypoint handles the first boot for you: it runs migrations, imports the dataset, and trains the PESTLE model if its artifact is missing — then starts Gunicorn.

### Option 2: Local development (SQLite fallback)
```bash
# create a virtual environment and install dependencies (uses pyproject.toml)
uv venv && uv sync
source .venv/bin/activate

python manage.py migrate
python manage.py import_insights   # clean + load data/jsondata.json
python manage.py train_model       # train the PESTLE classifier
python manage.py runserver
```
Without a `DATABASE_URL`, Django falls back to the local `db.sqlite3`.

## Dashboard Features

### Key Performance Indicators (KPIs)
- Total Insights
- Total Sectors Covered
- Total Countries Covered
- Average Intensity
- Average Likelihood
- High Impact Insights

### Sector & Topic Intelligence
- Insights by Sector
- Top Discussed Topics (Oil, Gas, Consumption, etc.)
- Sector vs Topic distribution

### Geographic Analysis
- Country-level insight distribution
- Region vs Sector comparison

### Risk & Impact Analysis
- Risk Matrix (Likelihood vs Intensity)
- Intensity distribution across insights
- Identification of high-impact, medium-likelihood issues

### PESTLE & Trend Analysis
- PESTLE category distribution
- Time-based trends using published dates

### Insight Explorer
- Detailed drill-down table
- Interactive HTMX filtering across all dimensions (filters are also reflected in the URL)

All aggregations are computed **server-side** in Django services; the frontend only draws the charts from injected JSON specs.

## Machine Learning: PESTLE Classifier

A supervised model that predicts the PESTLE category (Political, Economic, Social, Technological, Legal, Environmental) of an insight from its `title`.

- **Pipeline:** TF-IDF over the title + one-hot encoding of `sector`/`topic`/`region`/`country`/`source` + median-imputed numerics (`intensity`, `likelihood`, `relevance`, publication year/month, forecast span) → **LinearSVC**
- **Evaluation:** stratified train/test split (80/20, seed 42) with 5-fold cross-validation on the training split; scored once on the held-out test set against a majority-class baseline
- **Results** (on the 907 labelled rows of the shipped dataset): **~71% test accuracy** and 0.64 macro-F1 vs a 38% majority-class baseline — recorded in `ml/artifacts/metrics.json`
- **In the dashboard:**
  - `/predict/` — enter an insight title and get the predicted PESTLE label with top-3 relative confidences (softmax-normalized decision scores)
  - `/model-metrics/` — model quality report: accuracy, macro-F1, per-class report, and confusion matrix
- **Design notes:** hyperparameters were tuned in `ml/notebooks/pestle_baseline.ipynb` and the winning pipeline frozen in `ml/training.py`; the fitted model is saved as `ml/artifacts/pestle_pipeline.joblib` (gitignored — train it with `python manage.py train_model`), while `metrics.json` is committed so the metrics page and tests work without retraining. Predictions degrade gracefully: a missing model or too-short input returns a friendly error message instead of crashing the page.

## Business Use Case

Enerlytics supports:
- **Business Intelligence & Reporting**
- **Strategic Planning**
- **Market & Sustainability Monitoring**
- **Executive Decision Support**

The dashboard helps stakeholders quickly understand **what is happening, where, and how impactful it is**.

## Dataset Description

The bundled dataset (`data/jsondata.json`) contains **1,000 curated energy/sustainability insights**. Each record includes:

- `title`, `insight`, `url` — the insight itself and its source link
- `sector`, `topic` — domain classification
- `country`, `region` — geographic attribution
- `intensity`, `likelihood`, `relevance`, `impact` — scoring metrics
- `pestle` — PESTLE category (Political, Economic, Social, Technological, Legal, Environmental)
- `source`, `added`, `published` — provenance and timeline
- `start_year`, `end_year` — projection horizon

The `import_insights` command normalizes the raw JSON before loading: it trims whitespace, converts `""` placeholders to NULLs, parses date strings, and discards out-of-range forecast years (2000–2100 window).

## Project Structure
```
enerlytics/
├── config/            # Django project settings & URLs
├── dashboard/         # Dashboard views, templates (HTMX partials), URLs
├── insights/          # Insight model, filtering/aggregation services,
│                      #   and the import_insights management command
├── ml/                # PESTLE classifier: training pipeline, prediction API,
│                      #   train_model command, notebook, and artifacts
├── data/              # Source dataset (jsondata.json)
├── static/            # CSS, Chart.js rendering logic, screenshots
├── templates/         # Base template (HTMX + Chart.js)
├── Dockerfile         # Production container build
├── docker-entrypoint.sh # First-boot setup: migrate, import data, train model
└── docker-compose.yml # Web + Postgres (pgvector) services
```

## Testing
```bash
pytest
```

## Key Takeaways

- Energy sector dominates global insights
- Oil and gas remain primary focus topics
- Northern America is the most represented region
- Most insights fall into **medium-likelihood, high-impact** category
- Environmental risks are region-specific and supply-chain driven

---
