# Run ETL Anomaly Monitor Locally
- Python 3.10 or newer
- Windows PowerShell

## 1. Open the project folder

Open PowerShell in the folder containing `pyproject.toml` and `dashboard.py`.
From the repository root, enter the application folder:

```powershell
cd etl-anomaly-monitor
```

Run the remaining commands from this application folder.

## 2. Set up Python (first time only)

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dashboard,dev]"
```

If `py` is unavailable, use `python -m venv .venv` for the first command.
These instructions use the virtual environment's Python directly, so activation is unnecessary.

## 3. Generate demo data

```powershell
.\.venv\Scripts\python.exe -m etl_monitor.cli demo
```

This processes synthetic normal and abnormal CSV batches and creates `data/monitor.db`.
The demo provides history for Isolation Forest, which starts after 20 prior runs classified as normal.

## 4. Open the dashboard

```powershell
.\.venv\Scripts\python.exe -m streamlit run dashboard.py
```

Open **http://localhost:8501** if the browser does not open automatically.
In the dashboard's **SQLite database** field, enter:

```text
data/monitor.db
```

## 5. Process a CSV and view history

Run these commands while the dashboard is stopped, or in another PowerShell window opened in the same project folder:

```powershell
.\.venv\Scripts\python.exe -m etl_monitor.cli run data/sample_orders.csv
.\.venv\Scripts\python.exe -m etl_monitor.cli history
```

To process your own CSV, replace `data/sample_orders.csv` with its path. Required headers:

```csv
order_id,customer_id,amount,order_date
A001,C001,150.00,2026-01-10
```

Use nonblank order/customer IDs, positive finite amounts, and dates in `YYYY-MM-DD` format. Use synthetic or authorized data.

## Run again later

Open PowerShell in the project folder and start the dashboard:

```powershell
.\.venv\Scripts\python.exe -m streamlit run dashboard.py
```

Your database is saved locally; setup and demo generation do not need to be repeated.

## Troubleshooting

- **Python path is not recognized:** confirm you are in the folder containing `pyproject.toml`, then complete step 2 to create `.venv` there.
- **No module named `etl_monitor` or `streamlit`:** repeat the installation command in step 2.
- **No monitoring data appears:** run step 3, confirm the database field is `data/monitor.db`, then refresh the dashboard. A different working folder may require the full database path.
- **Already have a database elsewhere?** Enter its full path in the dashboard. To write CLI results to that database too, put `--db` before the command and replace the example path below with your database's location:

  ```powershell
  .\.venv\Scripts\python.exe -m etl_monitor.cli --db "C:\path\to\monitor.db" run data/sample_orders.csv
  ```

