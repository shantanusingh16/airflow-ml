"""Minimal job-runner entrypoint.

Executes a Python job script (first CLI argument) with any remaining
arguments. Keeps job containers trivial: jobs are plain .py files, shared
conventions live here.

Environment (injected by the Airflow DAG via DockerOperator `environment=`):
    JOB_ID           name of the job / task
    RUN_ID           Airflow DAG run id (used to scope S3 artifact keys)
    S3_ENDPOINT      e.g. http://minio:9000
    S3_BUCKET        artifact bucket, e.g. ml-artifacts
    S3_REGION        e.g. us-east-1
    S3_ACCESS_KEY    S3 access key
    S3_SECRET_KEY    S3 secret key

A non-zero exit code from the job script fails the Airflow task;
a traceback from an unhandled exception does the same (container exits 1).
"""

from __future__ import annotations

import os
import runpy
import sys


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: runner.py <job-script.py> [job-args ...]", file=sys.stderr)
        return 64  # EX_USAGE

    script = sys.argv[1]
    job_args = sys.argv[2:]

    print(
        f"[job-runner] JOB_ID={os.environ.get('JOB_ID')} "
        f"RUN_ID={os.environ.get('RUN_ID')} "
        f"bucket={os.environ.get('S3_BUCKET')}"
    )
    print(f"[job-runner] executing {script} args={job_args}")

    if not os.path.exists(script):
        print(f"[job-runner] ERROR: job script not found: {script}", file=sys.stderr)
        return 66  # EX_NOINPUT

    # Run the job module as __main__ so `if __name__ == "__main__"` works.
    sys.argv = [script] + job_args
    runpy.run_path(script, run_name="__main__")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit as exc:
        # Jobs may sys.exit(code); propagate the code as the container status.
        code = exc.code
        if isinstance(code, str) and code:
            # sys.exit("message"): print it — otherwise the message is lost and
            # the job looks like it died silently (container just exits 1).
            print(code, file=sys.stderr)
        raise SystemExit(code if isinstance(code, int) else (0 if code is None else 1))