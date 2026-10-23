# ETL Anomaly Monitor

A **learning-first data engineering starter** that extracts order data from CSV files, cleans and loads valid records into SQLite, measures data quality, and flags unusual pipeline runs using **transparent rules + Isolation Forest**.

> This is a working prototype for learning and experimentation, **not a completed undergraduate thesis** or a production monitoring system. The included data is synthetic, and the detector's accuracy has not been validated on real pipelines.

## What you can do now

- Run a CSV → cleaning → SQLite ETL pipeline.
- Calculate per-run data quality metrics: row counts, missing fields, duplicates, invalid amounts/dates, and mean amount.
- Flag obvious problems with explainable thresholds.
- Use **Isolation Forest** once **20 prior healthy runs** are available. The model learns from run-level metrics, **not raw customer records**.
- Keep run history and detected reasons in a local SQLite database.
- Generate synthetic baseline and anomaly batches.
- Explore results in a Streamlit dashboard.
- Run automated tests.

## 1. Set up (Windows 11 / PowerShell)

From the extracted project directory:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dashboard,dev]"
```

If `py -3` is not available, use `python -m venv .venv`.

If PowerShell blocks virtual environment activation, run the commands with `.\.venv\Scripts\python.exe` instead of changing execution policy.

## 2. Run a simple ETL batch

```powershell
etl-monitor run data/sample_orders.csv
etl-monitor history
```

The first command reads `data/sample_orders.csv`, validates rows, inserts new valid orders into `data/monitor.db`, and stores monitoring metrics. Re-running the same file doesn't insert the same order IDs twice; each attempt is still recorded in run history.

## 3. Generate enough history to activate ML

```powershell
etl-monitor demo
etl-monitor history --limit 10
```

The demo generates **25 mostly normal runs** and **five abnormal scenarios**: volume drop, missing customer IDs, duplicate order IDs, invalid amounts, and a large amount distribution shift.

- Synthetic CSV files are written to `data/demo_inputs/` (ignored by Git).
- Run history and loaded orders live in `data/monitor.db` (also ignored by Git).
- The first 20 healthy runs use only quality rules. Later runs use rules **and** an Isolation Forest trained exclusively on earlier runs classified as normal.
- Some benign runs may be flagged and some anomalies may be missed; that is expected from an unvalidated baseline model.

## 4. Open the monitoring dashboard

```powershell
streamlit run dashboard.py
```

Streamlit usually opens a local browser tab. You can browse run metrics, model scores, detection reasons, and the history table.

## 5. Run tests

```powershell
pytest -q
```

## Project structure

```text
etl-anomaly-monitor/
├── AGENTS.md                  # Guidance when using Codex in this repository
├── README.md
├── pyproject.toml            # Python dependencies and command registration
├── dashboard.py              # Streamlit run-history dashboard
├── data/
│   └── sample_orders.csv     # Small tracked example input
├── docs/
│   ├── ARCHITECTURE.md       # Data flow and detector design
│   └── CODEX_ROADMAP.md     # Suggested incremental improvements/prompts
├── src/etl_monitor/
│   ├── cli.py                # Commands: run, demo, history
│   ├── database.py           # SQLite tables and queries
│   ├── detection.py          # Rules and Isolation Forest
│   ├── demo.py               # Synthetic CSV generation
│   └── pipeline.py           # Extract, validate, load, record run
└── tests/                    # Automated tests
```

## Data contract

CSV input must have these four headers:

```csv
order_id,customer_id,amount,order_date
A001,C001,150.00,2026-01-10
```

- `order_id`: nonblank, unique inside a batch, globally unique in the destination table.
- `customer_id`: nonblank.
- `amount`: numeric and greater than zero.
- `order_date`: `YYYY-MM-DD`.

Invalid rows are discarded from loading and counted in quality metrics. The original files are not changed. This is intentionally minimal; a production design would include a quarantine table, detailed row-level errors, better transaction auditing, and configuration-driven pipelines.

## Good first places to read

1. `src/etl_monitor/pipeline.py` — where ETL happens.
2. `src/etl_monitor/detection.py` — the anomaly model and quality rules.
3. `src/etl_monitor/database.py` — the tables and persistent records.
4. `docs/CODEX_ROADMAP.md` — how to expand the project one feature at a time.

## Research path (not yet implemented)

For an undergraduate research project, a stronger contribution would compare *rule-only*, *Isolation Forest*, and another detector (e.g. One-Class SVM or an autoencoder) on a **labeled** set of realistic ETL anomalies. Report precision, recall, F1, false-positive rate, and training/inference costs, then study performance under changing workloads and unseen anomaly types. Avoid treating synthetic demonstration accuracy as proof of real-world effectiveness.

## Known limitations

- Single orders pipeline; no orchestration/scheduler, API source, or multi-stage pipelines yet.
- Schema errors stop processing before a run is recorded.
- `INSERT OR IGNORE` skips previously loaded order IDs but doesn't track cross-batch conflicts as a quality metric.
- Detection happens on aggregates **per batch**, not individual row outliers.
- The model is refit for each run after warm-up; this is acceptable for a small learning prototype but inefficient at scale.
- Thresholds and model hyperparameters are illustrative, not tuned or validated.
- SQLite is local, not a cloud data warehouse.
- No authentication, alert delivery, production operations, or PII safeguards for real data.

**Use synthetic or properly authorized data.** Do not add real student/customer personal data to this repository.

## GitHub: your first commit

Create a new **empty** repository on GitHub, then run these commands in the extracted folder (replace `YOUR_USERNAME`):

```powershell
git init
git branch -M main
git add .
git commit -m "Initial ETL anomaly monitoring prototype"
git remote add origin https://github.com/YOUR_USERNAME/etl-anomaly-monitor.git
git push -u origin main
```

Do not include auto-generated GitHub README/.gitignore/license in the new repository if you want a straightforward first push; this starter already has those files.
