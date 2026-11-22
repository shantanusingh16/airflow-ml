# t_18f19dba / impl-1

## Prompt as dispatched

````
---
factory:
  base: HEAD
---

# Ticket t_18f19dba — Pass AIRFLOW_PROJ_DIR into containers; remove the hardcoded host path

Project: airflow-ml (git). Work on branch `factory/t_18f19dba/impl-1` from `HEAD`.
Commit only source changes. Do NOT touch `.env` (gitignored, operator-owned) and do NOT touch
`.factory/` (operator-owned deploy/routing layer).

## Problem
`dags/jobtask.py` line 15 builds DockerOperator bind mounts from

    PROJECT_DIR = os.environ.get("AIRFLOW_PROJ_DIR", "/run/media/shantanu/Volume/Projects/airflow-ml")

but `docker-compose.yml` only uses `AIRFLOW_PROJ_DIR` for its own volume paths and never passes it
into the containers. Inside `airflow-worker` the variable is unset, so every job mounts the hardcoded
path of the operator's machine. That only works on this one host; in staging it made GPU jobs try to
mount the live project's `dags/` and `triton-models/` (refused by the staging policy).

## Changes (all four, nothing else)

1. `docker-compose.yml`: add `AIRFLOW_PROJ_DIR: ${AIRFLOW_PROJ_DIR}` (no `:-` default — an unset/empty
   value must be visible, not silently defaulted) to the `environment:` block of the
   `x-airflow-common` anchor (the `&airflow-common-env` block, i.e. the block starting around line 21,
   right after `AIRFLOW__API__SECRET_KEY` or alongside the other S3/JOB_* entries). Every airflow-*
   service (airflow-init, airflow-conn-init, airflow-apiserver, airflow-scheduler, airflow-dag-processor,
   airflow-worker, airflow-triggerer, flower) merges that anchor, so this one addition covers all of them.

2. `dags/jobtask.py` line 15: remove the hardcoded default. Resolve the variable and, if it is unset
   or empty, fail at DAG-parse time with a clear error message that names `AIRFLOW_PROJ_DIR` and says it
   must be set in `.env` / docker-compose environment, e.g.:

       PROJECT_DIR = os.environ.get("AIRFLOW_PROJ_DIR")
       if not PROJECT_DIR:
           raise AirflowException(
               "AIRFLOW_PROJ_DIR is not set (or is empty). Set it in .env / the docker-compose "
               "environment to the host path of the airflow-ml project directory; it is used to "
               "bind-mount dags/, config/ and triton-models/ into job containers."
           )

   (`AirflowException` is already imported in this file.) Keep `TRITON_MODEL_STORE = f"{PROJECT_DIR}/triton-models"`
   derived from `PROJECT_DIR` exactly as today — only the source of `PROJECT_DIR` changes.

3. Keep everything else in `dags/jobtask.py` unchanged (S3_* fallbacks, JOB_* images, ML platform URLs).

4. `README.md`: in the "Configuration (`.env`)" table (around line 208), mark `AIRFLOW_PROJ_DIR` as
   REQUIRED (no default) — it is the host path mapped to `/opt/airflow/dags` + `config/` AND is passed
   into every airflow-* container so job containers' bind mounts resolve on the correct host. Adjust the
   table row accordingly (e.g. replace the "this directory" default with "required — no default").

## Acceptance checks you must run before committing
- `grep -rn "/run/media" dags/` → no matches.
- `python3 -m py_compile dags/jobtask.py` (or `ast.parse`) → compiles. (The sandbox has no Airflow
  install; do not try to import airflow.)
- Structural check that every `airflow-*` service gets the variable: YAML-parse `docker-compose.yml`,
  resolve the `x-airflow-common` anchor, and assert `AIRFLOW_PROJ_DIR` appears in the effective
  `environment` of each service that merges `<<: *airflow-common`. (The sandbox has no docker binary —
  `docker compose config` is NOT runnable here; do the YAML check instead and say so in your summary.)
- `git status --short` shows only `docker-compose.yml`, `dags/jobtask.py`, `README.md` modified
  (plus nothing under `.env` / `.factory/`).

## Out of scope (operator handles these after the branch is reviewed)
- Staging verification: `sudo factory-staging up airflow-ml --ref factory/t_18f19dba/impl-1` with the
  `service_env` workaround removed from `.factory/deploy.yaml`, then trigger the `gpu_probe` DAG and
  check `sudo factory-staging logs airflow-ml shim` for refused creates.
- Removing the `service_env:` workaround block from `.factory/deploy.yaml` (operator-owned file).

Report in your final summary: the exact diff (or per-file change list), the grep/compile/YAML check
outputs, and the branch tip SHA.
````

## Dispatch record

```json
{
  "argv0": "/home/dev-runner/.local/bin/omp",
  "artifacts": [],
  "base_ref": "HEAD",
  "base_sha": "569bd027a2b6065b6e439698d399bc32f314c38b",
  "binary": "/home/dev-runner/.local/bin/omp",
  "branch": "factory/t_18f19dba/impl-1",
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
  "exit_file": "/srv/software-factory/.dispatch/t_18f19dba--impl-1.exit",
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
  "job_dir": "/srv/factory-jobs/t_18f19dba--impl-1",
  "mode": "print",
  "project": "airflow-ml",
  "project_real": "/run/media/shantanu/Volume/Projects/airflow-ml",
  "prompt_file": "/srv/software-factory/.dispatch/t_18f19dba--impl-1.md",
  "prompt_sha256_prefix": "38f42190a3537469",
  "resolved_via": "function_default",
  "routing_sha256_prefix": "a1ce7f45d24409f3",
  "secrets": [],
  "spec_sha256": "7ed81ef045c649067462c14d0845f1d283dbb00d364dee0c78fdd87ddc6d5fce",
  "ticket": "t_18f19dba",
  "transcript": "/srv/factory-jobs/t_18f19dba--impl-1/transcript.log",
  "transcript_sha256": "ade8de108071c2f7837ee36a11ab45dfc58c159dd663c16d99dbdee78c50e182",
  "window": "impl-1",
  "workdir": "/run/media/shantanu/Volume/Projects/airflow-ml",
  "workdir_rel": "."
}
```
