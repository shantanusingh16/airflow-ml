#!/usr/bin/env python3
"""Show recent DAG runs and task-instance states via the Airflow 3 REST API.

Usage: runinfo.py <api_token> <dag_id> <airflow_host>
"""

from __future__ import annotations

import json
import sys
import urllib.request


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("usage: runinfo.py <api_token> <dag_id> <airflow_host>")
    token, dag, host = sys.argv[1], sys.argv[2], sys.argv[3].rstrip("/")

    def req(path: str) -> dict:
        r = urllib.request.Request(
            f"{host}/api/v2{path}", headers={"Authorization": f"Bearer {token}"}
        )
        with urllib.request.urlopen(r) as f:
            return json.load(f)

    runs = req(f"/dags/{dag}/dagRuns?limit=25&order_by=-logical_date").get("dag_runs", [])
    if not runs:
        print(f"no dag runs found for {dag}")
        return
    for run in runs:
        run_id = run.get("dag_run_id") or run.get("run_id") or "?"
        print(f"{run_id:44s} state={run['state']:10s} logical={run.get('logical_date')}")
        for ti in req(f"/dags/{dag}/dagRuns/{run_id}/taskInstances?limit=100").get(
            "task_instances", []
        ):
            print(f"    {ti['task_id']:20s} {ti['state']}")


if __name__ == "__main__":
    main()