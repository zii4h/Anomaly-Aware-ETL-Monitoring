"""Command line entrypoint: run, demo, and history."""

from __future__ import annotations

import argparse
from contextlib import closing
import json
from pathlib import Path

from .database import DEFAULT_DB, fetch_runs, open_db
from .demo import run_demo
from .pipeline import process_csv


def _print_run(run: dict) -> None:
    print(f"Run #{run['run_id']} | {run['status'].upper()} | {run['detector']}")
    print(f"  input={run['input_rows']} valid={run['valid_rows']} loaded={run['loaded_rows']}")
    if run["anomaly_score"] is not None:
        print(f"  model_score={run['anomaly_score']:.4f} (negative means ML outlier)")
    for reason in run["reasons"]:
        print(f"  ! {reason}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Starter ETL anomaly monitoring project")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="SQLite database path")
    subcommands = parser.add_subparsers(dest="command", required=True)

    run = subcommands.add_parser("run", help="Load and monitor one CSV batch")
    run.add_argument("csv", type=Path, help="CSV with order_id,customer_id,amount,order_date")
    run.add_argument("--pipeline", default="orders_etl")

    demo = subcommands.add_parser("demo", help="Generate synthetic normal and anomalous runs")
    demo.add_argument("--normal-runs", type=int, default=25)
    demo.add_argument("--output-dir", type=Path, default=Path("data/demo_inputs"))

    history = subcommands.add_parser("history", help="Show recent runs")
    history.add_argument("--limit", type=int, default=15)
    history.add_argument("--pipeline", default="orders_etl")
    history.add_argument("--json", action="store_true", help="Output raw run records")

    args = parser.parse_args(argv)
    try:
        if args.command == "run":
            _print_run(process_csv(args.csv, db_path=args.db, pipeline_name=args.pipeline))
        elif args.command == "demo":
            results = run_demo(db_path=args.db, output_dir=args.output_dir, normal_runs=args.normal_runs)
            print(f"Generated {len(results)} synthetic input batches; saved history to {args.db}")
            for scenario, result in results:
                if scenario != "normal":
                    print(f"\n{scenario}:")
                    _print_run(result)
            normal_count = sum(1 for kind, result in results if kind == "normal" and result["status"] == "normal")
            print(f"\nNormal baseline: {normal_count}/{args.normal_runs} runs classified normal")
        elif args.command == "history":
            with closing(open_db(args.db)) as conn:
                runs = fetch_runs(conn, pipeline_name=args.pipeline, limit=args.limit)
            if args.json:
                print(json.dumps(runs, indent=2))
            else:
                if not runs:
                    print("No runs yet. Try: etl-monitor demo")
                for run in runs:
                    print(f"#{run['run_id']:>3} {run['started_at_utc']}  {run['status']:<7} "
                          f"input={run['input_rows']:<4} loaded={run['loaded_rows']:<4} "
                          f"score={run['anomaly_score']}")
    except (FileNotFoundError, ValueError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
