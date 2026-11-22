# t_d0cb9b72 / egm-review

## Prompt as dispatched

````
---
factory:
  base: factory/t_d0cb9b72/impl-1
---

# Review ticket t_d0cb9b72 (branch factory/t_d0cb9b72/impl-1) — remove the hardcoded AIRFLOW_PROJ_DIR fallback in examples/detection/infer_cli.py

Project: airflow-ml (git). Review branch `factory/t_d0cb9b72/impl-1` against its base `HEAD` (base commit 569bd02).
Implementation commit: 089edea (record commit c39c2fc is factory provenance, not reviewable code).

## Ticket intent
`examples/detection/infer_cli.py` (a host-side dev CLI, no airflow imports) resolved
`PROJECT_DIR = Path(os.environ.get("AIRFLOW_PROJ_DIR", "/run/media/shantanu/Volume/Projects/airflow-ml"))`
— the same host-specific fallback that sibling ticket t_18f19dba removed from `dags/jobtask.py`.
After t_18f19dba, `AIRFLOW_PROJ_DIR` is required (set in `.env`, no default) and passed into every
airflow-* container, so the fallback is no longer needed anywhere. Change: drop the default; fail
with a clear message naming the variable when unset/empty (plain `RuntimeError` is acceptable for
this CLI; mirror the wording style of the guard in `dags/jobtask.py` — visible on branch
`factory/t_18f19dba/impl-1`). `docs/` must stay untouched (operator documentation).

## Changes the implementation must contain (and only these)
1. `examples/detection/infer_cli.py` (previously lines 48-49): replace the two-line
   `os.environ.get("AIRFLOW_PROJ_DIR", "/run/media/...")` with a no-default read + a guard that
   raises `RuntimeError` naming `AIRFLOW_PROJ_DIR` and where to set it; `PROJECT_DIR` must remain a
   `Path` object (re-wrapped via `Path(PROJECT_DIR)`) because the following line does
   `PROJECT_DIR / "triton-models" / MODEL_NAME / "model_info.json"`.
2. No changes to `dags/`, `docker-compose.yml`, `jobrunner/`, `docs/`, `.env`, or any other file.

## Verified by the orchestrator (re-check if cheap, else trust and focus on code quality)
- `git grep -n "/run/media" <branch> -- examples/` → no matches on the branch.
- `python3 -m py_compile` on the branch version of the file → exit 0.
- Executing the module-top section with `AIRFLOW_PROJ_DIR` unset → `RuntimeError: AIRFLOW_PROJ_DIR
  is not set (or is empty). Set it in .env / the environment …`; with the variable set → module top
  executes and `PROJECT_DIR` is a `PosixPath`.

## Questions for your review
- Is the guard message clear and consistent in style with the `dags/jobtask.py` guard
  (compare with branch `factory/t_18f19dba/impl-1`)?
- Any other spot in `examples/` (or anywhere outside `dags/`) that still assumes the old fallback or
  references `/run/media`?
- Do `MODEL_INFO_JSON` default and `load_model_info()` still behave sensibly now that `PROJECT_DIR`
  is a `Path` re-wrapped from the raw string?
- Diff hygiene: only `examples/detection/infer_cli.py` changed, no stray edits, commit message accurate.

Report findings with severity (blocker/major/minor/nit), file:line references, and a verdict:
APPROVE / APPROVE-WITH-NITS / CHANGES-REQUIRED.
````

## Dispatch record

```json
{
  "argv0": "/home/dev-runner/.local/bin/claude",
  "artifacts": [],
  "base_ref": "factory/t_d0cb9b72/impl-1",
  "base_sha": "c39c2fcd95627560e66d0b82e288f8dabc77a766",
  "binary": "/home/dev-runner/.local/bin/claude",
  "branch": "factory/t_d0cb9b72/egm-review",
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
  "exit_file": "/srv/software-factory/.dispatch/t_d0cb9b72--egm-review.exit",
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
  "job_dir": "/srv/factory-jobs/t_d0cb9b72--egm-review",
  "mode": "print",
  "project": "airflow-ml",
  "project_real": "/run/media/shantanu/Volume/Projects/airflow-ml",
  "prompt_file": "/srv/software-factory/.dispatch/t_d0cb9b72--egm-review.md",
  "prompt_sha256_prefix": "3054483def310372",
  "resolved_via": "project_override",
  "routing_sha256_prefix": "a1ce7f45d24409f3",
  "secrets": [
    "ANTHROPIC_API_KEY",
    "CLAUDE_CODE_OAUTH_TOKEN"
  ],
  "spec_sha256": "5e4f7ee9fadf58878757e7b93f7da80ce968c3f9232c0e6acb6802a6db19c0aa",
  "ticket": "t_d0cb9b72",
  "transcript": "/srv/factory-jobs/t_d0cb9b72--egm-review/transcript.log",
  "transcript_sha256": "52ca42ab1491aa1ac0c2df11c973c05777bb6dd9260a96353378f6e64e188ad9",
  "window": "egm-review",
  "workdir": "/run/media/shantanu/Volume/Projects/airflow-ml",
  "workdir_rel": "."
}
```
