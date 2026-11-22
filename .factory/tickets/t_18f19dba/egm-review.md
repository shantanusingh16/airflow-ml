# t_18f19dba / egm-review

## Prompt as dispatched

````
---
factory:
  base: factory/t_18f19dba/impl-1
---

# Review ticket t_18f19dba (branch factory/t_18f19dba/impl-1) — Pass AIRFLOW_PROJ_DIR into containers; remove the hardcoded host path

Project: airflow-ml (git). Review branch `factory/t_18f19dba/impl-1` against `HEAD` (base commit 569bd02).
Implementation commit: c3faafe (record commit 5d59f5b is factory provenance, not reviewable code).

## Ticket intent
`dags/jobtask.py` built DockerOperator bind mounts from
`PROJECT_DIR = os.environ.get("AIRFLOW_PROJ_DIR", "/run/media/shantanu/Volume/Projects/airflow-ml")`,
but docker-compose.yml never passed AIRFLOW_PROJ_DIR into the airflow containers, so workers on other
hosts fell back to the operator-machine path. Fix: pass the variable into every airflow-* container via
the x-airflow-common environment anchor, and make the DAG code fail loudly at parse time when it is unset.

## Changes the implementation must contain (and only these)
1. `docker-compose.yml`: `AIRFLOW_PROJ_DIR: ${AIRFLOW_PROJ_DIR}` (no `:-` default) added to the
   `x-airflow-common` environment anchor, so every airflow-* service (init, conn-init, apiserver,
   scheduler, dag-processor, worker, triggerer, flower, airflow-cli) receives it.
2. `dags/jobtask.py`: hardcoded default removed; when `AIRFLOW_PROJ_DIR` is unset/empty, raise at
   import/parse time an `AirflowException` whose message names the variable and where to set it.
   `TRITON_MODEL_STORE` must stay `f"{PROJECT_DIR}/triton-models"`; S3_*/JOB_*/ML fallbacks unchanged.
3. `README.md`: `AIRFLOW_PROJ_DIR` documented as required (no default) in the Configuration(.env) table.
4. No changes to `.env` or `.factory/`; no other files touched.

## Verified by the orchestrator (re-check if cheap, else trust and focus on code quality)
- `grep -rn "/run/media" dags/` → no matches on the branch.
- `docker compose config` (compose v5.7.1, branch checkout + operator .env) renders
  `AIRFLOW_PROJ_DIR: /run/media/shantanu/Volume/Projects/airflow-ml` in the environment of every
  default-profile airflow-* service.
- `python3 -m py_compile dags/jobtask.py` passes.

## Questions for your review
- Is the parse-time failure behavior correct and safe for Airflow 3.3.1 (exception type, import-time
  side effects, effect on the scheduler's dagbag import)? Any risk to services that never import jobtask?
- Does the compose change interact badly with `docker compose config` when AIRFLOW_PROJ_DIR is unset
  (empty-string env vs missing key)? Is "no default" the right call for the container env?
- Any missing edge cases (e.g. other files that assume PROJECT_DIR is always set, docs that contradict)?
- Diff hygiene: only the three source files, no stray edits, commit message accurate.

Report findings with severity (blocker/major/minor/nit), file:line references, and a verdict:
APPROVE / APPROVE-WITH-NITS / CHANGES-REQUIRED.
````

## Dispatch record

```json
{
  "argv0": "/home/dev-runner/.local/bin/claude",
  "artifacts": [],
  "base_ref": "factory/t_18f19dba/impl-1",
  "base_sha": "5d59f5b5b3aa9e1653354c3c8f50f6d89a47e9c4",
  "binary": "/home/dev-runner/.local/bin/claude",
  "branch": "factory/t_18f19dba/egm-review",
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
      "egress-proxy": {
        "port": 8889
      }
    },
    "via": "policy_default"
  },
  "exit_file": "/srv/software-factory/.dispatch/t_18f19dba--egm-review.exit",
  "function": "egm_review",
  "harness": "claude",
  "home_seed": [
    ".claude/settings.json",
    ".claude/plugins",
    ".claude.json"
  ],
  "install_roots": [
    "/home/dev-runner/.npm-global",
    "/home/dev-runner/.local"
  ],
  "job_dir": "/srv/factory-jobs/t_18f19dba--egm-review",
  "mode": "print",
  "project": "airflow-ml",
  "project_real": "/run/media/shantanu/Volume/Projects/airflow-ml",
  "prompt_file": "/srv/software-factory/.dispatch/t_18f19dba--egm-review.md",
  "prompt_sha256_prefix": "1813930b8ace226e",
  "resolved_via": "project_override",
  "routing_sha256_prefix": "a1ce7f45d24409f3",
  "secrets": [
    "ANTHROPIC_API_KEY",
    "CLAUDE_CODE_OAUTH_TOKEN"
  ],
  "spec_sha256": "e2df7d59716bba05204321116697122b0810ea5c86ff495f85de8a90fbfc69bb",
  "ticket": "t_18f19dba",
  "transcript": "/srv/factory-jobs/t_18f19dba--egm-review/transcript.log",
  "transcript_sha256": "be4b5386832c22d6de30dd0b6d678bb46cc47caf1ff6c6a6999f1f782ec77625",
  "window": "egm-review",
  "workdir": "/run/media/shantanu/Volume/Projects/airflow-ml",
  "workdir_rel": "."
}
```
