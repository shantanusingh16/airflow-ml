# t_d0cb9b72 / impl-1

## Prompt as dispatched

````
---
factory:
  base: HEAD
---

# Task: remove hardcoded AIRFLOW_PROJ_DIR fallback in examples/detection/infer_cli.py

Ticket t_d0cb9b72, project airflow-ml.

## Background
Sibling ticket t_18f19dba removed the same host-specific hardcoded fallback
(`/run/media/shantanu/Volume/Projects/airflow-ml`) from `dags/jobtask.py` and made
`AIRFLOW_PROJ_DIR` a required environment variable: it is set in `.env` (no default) and
passed into every airflow-* container. t_18f19dba was scoped to `dags/` +
`docker-compose.yml`, so this file was left as found. After t_18f19dba, the fallback is no
longer needed anywhere: the variable is always provided by the environment.

## Exact change (ONLY file to modify: examples/detection/infer_cli.py)

Lines 48-49 currently read:

    PROJECT_DIR = Path(os.environ.get("AIRFLOW_PROJ_DIR",
                                      "/run/media/shantanu/Volume/Projects/airflow-ml"))

Replace with a no-default read plus a guard that fails with a clear message naming the
variable. This is a host-side dev CLI (it has no airflow imports), so use a plain
`RuntimeError` (no `AirflowException`); mirror the wording style of the guard in
`dags/jobtask.py` after t_18f19dba, which reads:

    PROJECT_DIR = os.environ.get("AIRFLOW_PROJ_DIR")
    if not PROJECT_DIR:
        raise AirflowException(
            "AIRFLOW_PROJ_DIR is not set (or is empty). Set it in .env / the docker-compose "
            "environment to the host path of the airflow-ml project directory; it is used to "
            "bind-mount dags/, config/ and triton-models/ into job containers."
        )

A suitable replacement here:

    PROJECT_DIR = os.environ.get("AIRFLOW_PROJ_DIR")
    if not PROJECT_DIR:
        raise RuntimeError(
            "AIRFLOW_PROJ_DIR is not set (or is empty). Set it in .env / the environment "
            "to the host path of the airflow-ml project directory; it is used to locate "
            "triton-models/<model>/model_info.json."
        )
    PROJECT_DIR = Path(PROJECT_DIR)

Semantics to preserve: `PROJECT_DIR` must remain a `Path` object, because line ~51 does
`PROJECT_DIR / "triton-models" / MODEL_NAME / "model_info.json"`. Do not import airflow.
Do not restructure anything else in the file. Small wording tweaks to the message are fine
as long as it names `AIRFLOW_PROJ_DIR` and says where to set it.

## Out of scope — do NOT touch
- `dags/`, `docker-compose.yml`, `jobrunner/` (t_18f19dba's scope)
- `docs/` (operator documentation, operator's call)
- `.env` (gitignored, operator-owned)
- everything else: the commit must contain ONLY the `examples/detection/infer_cli.py` change

## Acceptance (run in the checkout, show output in your final message)
1. `grep -rn "/run/media" examples/` — finds nothing (run it before step 2 so no
   `.pyc` from step 2 can interfere; a fresh checkout has no `__pycache__`).
2. `python3 -m py_compile examples/detection/infer_cli.py` — exit code 0.

## Commit
Commit only the source change. Message style: short imperative, ticket tag at the end,
e.g. `examples: require AIRFLOW_PROJ_DIR, drop hardcoded host path fallback (t_d0cb9b72)`.

## Final report
In your final message state: files changed, the branch tip SHA (`git rev-parse HEAD`), and
paste the acceptance command outputs.
````

## Dispatch record

```json
{
  "argv0": "/home/dev-runner/.local/bin/omp",
  "artifacts": [],
  "base_ref": "HEAD",
  "base_sha": "569bd027a2b6065b6e439698d399bc32f314c38b",
  "binary": "/home/dev-runner/.local/bin/omp",
  "branch": "factory/t_d0cb9b72/impl-1",
  "executor": {
    "image": "localhost/factory-runner@sha256:469e88d8ef36f40a287cae4e0fc8defcea71b25524a5a8f84dfa6986cea4f426",
    "isolation": "container",
    "key": "sandbox",
    "kind": "podman",
    "limits": {
      "cpus": "4",
      "memory": "8g",
      "pids": 4096,
      "shm": "64m"
    },
    "services": {
      "comfyui": {
        "port": 8188
      },
      "h3-jobs": {
        "port": 8288
      },
      "llama-swap": {
        "port": 8080
      }
    },
    "via": "policy_default"
  },
  "exit_file": "/srv/software-factory/.dispatch/t_d0cb9b72--impl-1.exit",
  "function": "code_implementation",
  "harness": "omp",
  "home_seed": [
    ".omp/agent/models.yml",
    ".omp/agent/config.yml",
    ".omp/agent/mcp.json",
    ".omp/plugins",
    ".pi/agent/pi-llama-swap.json"
  ],
  "install_roots": [
    "/home/dev-runner/.local",
    "/home/dev-runner/.omp/mcp",
    "/run/media/shantanu/Volume/Tools/pi-llama-swap"
  ],
  "job_dir": "/srv/factory-jobs/t_d0cb9b72--impl-1",
  "mode": "print",
  "project": "airflow-ml",
  "project_real": "/run/media/shantanu/Volume/Projects/airflow-ml",
  "prompt_file": "/srv/software-factory/.dispatch/t_d0cb9b72--impl-1.md",
  "prompt_sha256_prefix": "df6f73b73e01d815",
  "resolved_via": "function_default",
  "routing_sha256_prefix": "a1ce7f45d24409f3",
  "secrets": [],
  "spec_sha256": "2c1b94bcb5a04d9d252e76697313b6cdef32be9ebbd2327c7ea7b4d97e48bdf7",
  "ticket": "t_d0cb9b72",
  "transcript": "/srv/factory-jobs/t_d0cb9b72--impl-1/transcript.log",
  "transcript_sha256": "febcf8816382f7b3949cdd43f975d41f0a9dc0ed17a2bc717fa7da9822a6ab9a",
  "window": "impl-1",
  "workdir": "/run/media/shantanu/Volume/Projects/airflow-ml",
  "workdir_rel": "."
}
```
