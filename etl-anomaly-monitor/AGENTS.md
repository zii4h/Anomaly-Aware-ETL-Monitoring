# Codex repository guidance

This is a beginner-friendly Python ETL and anomaly-monitoring learning project.

- Prefer small, understandable changes. Explain any new concept briefly.
- Maintain the existing CLI commands, dashboard, and SQLite schema compatibility unless a migration is explicitly requested.
- Update/add tests for behavior changes; run `pytest -q` when dependencies are installed.
- Do not introduce cloud services, API keys, Docker, orchestration frameworks, or unnecessary dependencies without being asked.
- Keep synthetic examples separate from any real personal data.
- Do not claim the demo detector has validated real-world accuracy.
- For ML research changes, explicitly avoid train/test leakage and report false positives as well as true positives.
- Preserve the ability to run the project on Windows/PowerShell with Python 3.10+.
