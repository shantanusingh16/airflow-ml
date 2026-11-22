# t_18f19dba — Pass AIRFLOW_PROJ_DIR into containers; remove the hardcoded host path

Status: blocked · Assignee: engineering

## Body

factory:
  function: code_implementation
  base: HEAD

## Problem
dags/jobtask.py builds DockerOperator bind mounts from
  PROJECT_DIR = os.environ.get("AIRFLOW_PROJ_DIR", "/run/media/shantanu/Volume/Projects/airflow-ml")
but docker-compose.yml only uses AIRFLOW_PROJ_DIR for its own volume paths and never passes it into
the containers. Inside airflow-worker the variable is unset, so every job mounts the hardcoded path of
the operator's machine. That only works on this one host. In staging it made GPU jobs try to mount the
live project's dags/ and triton-models/ (refused by the staging policy).

## Change
1. docker-compose.yml: add `AIRFLOW_PROJ_DIR: ${AIRFLOW_PROJ_DIR}` to x-airflow-common.environment.
2. dags/jobtask.py: remove the hardcoded default. If AIRFLOW_PROJ_DIR is unset, fail at DAG-parse time
   with a clear message naming the variable.
3. Keep TRITON_MODEL_STORE derived from AIRFLOW_PROJ_DIR, as today.
4. Document AIRFLOW_PROJ_DIR in README/.env comments as required.

## Acceptance
- `grep -n "/run/media" dags/` finds nothing.
- `docker compose config` shows AIRFLOW_PROJ_DIR in the environment of every airflow-* service.
- Staging: `sudo factory-staging up airflow-ml --ref factory/<this card>/<window>` with the
  `service_env` workaround removed from .factory/deploy.yaml (ask the operator), then trigger the
  gpu_probe DAG: it succeeds, and `sudo factory-staging logs airflow-ml shim` shows no refused creates.
- The operator's Docker instance keeps working (.env already sets AIRFLOW_PROJ_DIR).

## Constraints
Commit only source changes. Don't touch .env (gitignored, operator-owned).

## Comments

- `1795369192` **engineering**: "**impl-1 complete** — branch `factory/t_18f19dba/impl-1`, tip `5d59f5b` (implementation commit `c3faafe`, record commit `5d59f5b`).\n\nDispatch log lines:\n- `2026-11-22 17:47:00 action=dispatch status=ok user=hermes ticket=t_18f19dba window=impl-1 window_id=@35 function=code_implementation harness=omp via=function_default mode=print executor=sandbox executor_via=policy_default isolation=container image=localhost/factory-runner@sha256:469e88d8… project=airflow-ml routing_sha=a1ce7f45d24409f3 prompt_sha=38f42190a3537469 workdir=/run/media/shantanu/Volume/Projects/airflow-ml meta=ok`\n- `2026-11-22 18:39:43 action=dispatch status=ok user=hermes ticket=t_18f19dba window=egm-review window_id=@37 function=egm_review harness=claude via=project_override mode=print executor=sandbox isolation=container … meta=ok`\n\nChanges on the branch (commit c3faafe):\n- `docker-compose.yml`: `AIRFLOW_PROJ_DIR: ${AIRFLOW_PROJ_DIR}` (no `:-` default) added to the `x-airflow-common` environment anchor.\n- `dags/jobtask.py`: hardcoded `/run/media/…` default removed; unset/empty `AIRFLOW_PROJ_DIR` now raises `AirflowException` at DAG-parse time naming the variable. `TRITON_MODEL_STORE` still derived from `PROJECT_DIR`.\n- `README.md`: `AIRFLOW_PROJ_DIR` marked required (no default) in the Configuration(.env) table.\n- Only those 3 files changed; `.env` and `.factory/` untouched.\n\nOrchestrator verification on the branch tip:\n- `grep -rn \"/run/media\" dags/` → no matches ✅\n- `docker compose config` (compose v5.7.1, branch checkout + operator .env) renders `AIRFLOW_PROJ_DIR: /run/media/shantanu/Volume/Projects/airflow-ml` in the environment of every default-profile airflow-* service (apiserver, conn-init, dag-processor, init, scheduler, triggerer, worker, flower); profile-gated `airflow-cli` also carries it (verified by YAML-anchor resolution) ✅\n- `python3 -m py_compile dags/jobtask.py` passes ✅\n\negm-review window dispatched and running; findings will be posted here. Remaining acceptan
- `1795369274` **engineering**: "**egm-review complete** — window `egm-review` (harness claude via project_override, executor sandbox/container) exited 0.\n\n- Review branch: `factory/t_18f19dba/egm-review` (record commit `9fc06e4`, base `5d59f5b` of impl-1).\n- Dispatch log line: `2026-11-22 18:39:43 action=dispatch status=ok user=hermes ticket=t_18f19dba window=egm-review window_id=@37 function=egm_review harness=claude via=project_override mode=print executor=sandbox isolation=container image=localhost/factory-runner@sha256:469e88d8… project=airflow-ml routing_sha=a1ce7f45d24409f3 prompt_sha=1813930b8ace226e meta=ok`\n- Reviewer verdict/findings text lives in `transcript.log` (owner-only: dev-runner) and the retained tmux pane. Read with:\n  - `sudo -u dev-runner /usr/bin/tmux -S /var/run/tmux-factory/dev capture-pane -p -t t_18f19dba:egm-review | tail -100`\n  - or `sudo cat /srv/factory-jobs/t_18f19dba--egm-review/transcript.log`\n  (hermes has no sudo path for those; the tmux session/windows persist via remain-on-exit until `factory-clean`.)\n\nReview scope covered: parse-time failure semantics for Airflow 3.3.1, empty-vs-missing env interpolation, edge cases (other files assuming PROJECT_DIR set), diff hygiene.\n\n**Remaining operator-gated acceptance** (per card): remove the `service_env` workaround from `.factory/deploy.yaml` (operator-owned), then `sudo factory-staging up airflow-ml --ref factory/t_18f19dba/impl-1`, trigger the `gpu_probe` DAG, and check `sudo factory-staging logs airflow-ml shim` for refused creates. Once the workaround is removed, hermes can run the staging up/logs steps (they are in the sudo allowlist); triggering gpu_probe and the deploy.yaml edit remain on the operator."
- `1795370306` **engineering**: "**Review (round 1, lens: artifact) — code-level acceptance independently verified; staging proof still operator-gated.**\n\nIndependent re-verification on branch `factory/t_18f19dba/impl-1` (tip `5d59f5b`, impl commit `c3faafe`; fresh `git archive` checkout + operator `.env`, compose v5.7.1):\n\n- **Acceptance 1** `grep -rn \"/run/media\" dags/` → no matches on the branch tip. ✅ (repo-wide scan: remaining hits are `docs/detection-example/*.md` sample commands, `examples/detection/infer_cli.py:49` fallback, and `.factory` ticket records — all outside this card's acceptance scope.)\n- **Acceptance 2** `docker compose --env-file <operator .env> config --format json`: all 9 airflow-* services carry `AIRFLOW_PROJ_DIR=/run/media/shantanu/Volume/Projects/airflow-ml` in their rendered environment — 7 in the default-profile render (apiserver, conn-init, dag-processor, init, scheduler, triggerer, worker) plus profile-gated `flower` (profiles: [\"flower\"]) and `airflow-cli` (profiles: [\"debug\"]) via the `x-airflow-common` env anchor (line 43). Non-airflow services correctly don't carry it; zero interpolation warnings. ✅\n  - *Narrative nit (non-blocking):* the handoff listed `flower` among the default-profile services; it is actually profile-gated. No functional difference.\n- **Change 2 (parse-time guard)** — executed, not just read: stub-import tests of `dags/jobtask.py` (real file, stubbed `airflow` pkgs): `AIRFLOW_PROJ_DIR` unset → `AirflowException` at import/parse time naming the variable; set to `\"\"` → same failure (empty case covered by `if not PROJECT_DIR`); set to a path → clean import, `TRITON_MODEL_STORE` = `<dir>/triton-models` (change 3 preserved). `py_compile` passes. ✅\n- **Change 4** README table row now reads \"required — no default\". (The `.env`-comment half can't be committed — `.env` is gitignored/operator-owned per the card's own constraint; `.env` is confirmed untracked on the branch and untouched.) ✅\n- **Constraints** impl commit `c3faafe` touch

## Events

- `1795365170` **created**: {"assignee": "engineering", "status": "ready", "parents": [], "creator_task_id": null, "tenant": null, "workspace_kind": "scratch", "workspace_path": null, "branch_name": null, "project_id": null, "skills": null, "goal_mode": null, "model_override": null, "provider_override": null}
- `1795365184` **edited**: null
- `1795365204` **claimed**: {"lock": "shantanu-ubuntu:284855", "expires": 1795366104, "run_id": 9}
- `1795365204` **spawned**: {"pid": 467138, "started_at": "bffb47f0-8c10-4c03-81ec-d65431d434c6:16|6107141"}
- `1795365204` **owner_admitted**: {"db": "/home/hermes/.hermes/profiles/engineering/state.db", "session_id": "local-9e197ed24ae86260c9c336e9d55594ebb5ef01e5dcaf08af6e93b61c6068965b", "request_id": "kanban:[\"airflow-ml\",\"t_18f19dba\",9]", "pid": 284855, "birth": 52562.74}
- `1795365205` **worker_bound**: {"pid": 467179, "claim_lock": "shantanu-ubuntu:284855", "started_at": "bffb47f0-8c10-4c03-81ec-d65431d434c6:16|6107180"}
- `1795365206` **heartbeat**: null
- `1795365282` **heartbeat**: null
- `1795365345` **heartbeat**: null
- `1795365415` **heartbeat**: null
- `1795365475` **heartbeat**: null
- `1795365550` **heartbeat**: null
- `1795365632` **heartbeat**: null
- `1795365702` **heartbeat**: null
- `1795365762` **heartbeat**: null
- `1795365850` **heartbeat**: null
- `1795365910` **heartbeat**: null
- `1795365976` **heartbeat**: null
- `1795366050` **heartbeat**: null
- `1795366110` **heartbeat**: null
- `1795366160` **heartbeat**: {"note": "impl-1 dispatched (omp/sandbox); waiting for .exit"}
- `1795366171` **heartbeat**: null
- `1795366231` **heartbeat**: null
- `1795366291` **heartbeat**: null
- `1795366351` **heartbeat**: null
- `1795366411` **heartbeat**: null
- `1795366471` **heartbeat**: null
- `1795366531` **heartbeat**: null
- `1795366591` **heartbeat**: null
- `1795366651` **heartbeat**: null
- `1795366731` **heartbeat**: null
- `1795366791` **heartbeat**: null
- `1795366858` **heartbeat**: null
- `1795366918` **heartbeat**: null
- `1795366978` **heartbeat**: null
- `1795367038` **heartbeat**: null
- `1795367098` **heartbeat**: null
- `1795367158` **heartbeat**: null
- `1795367218` **heartbeat**: null
- `1795367278` **heartbeat**: null
- `1795367338` **heartbeat**: null
- `1795367399` **heartbeat**: null
- `1795367399` **heartbeat**: {"note": "impl-1 (omp) still running, ~18 min"}
- `1795367459` **heartbeat**: null
- `1795367519` **heartbeat**: null
- `1795367579` **heartbeat**: null
- `1795367639` **heartbeat**: null
- `1795367699` **heartbeat**: null
- `1795367760` **heartbeat**: null
- `1795367820` **heartbeat**: null
- `1795367880` **heartbeat**: null
- `1795367940` **heartbeat**: null
- `1795368000` **heartbeat**: null
- `1795368081` **heartbeat**: null
- `1795368143` **heartbeat**: null
- `1795368223` **heartbeat**: null
- `1795368300` **heartbeat**: null
- `1795368384` **heartbeat**: null
- `1795368464` **heartbeat**: null
- `1795368524` **heartbeat**: null
- `1795368599` **heartbeat**: null
- `1795368679` **heartbeat**: null
- `1795368740` **heartbeat**: null
- `1795368800` **heartbeat**: null
- `1795368873` **heartbeat**: null
- `1795368942` **heartbeat**: null
- `1795369002` **heartbeat**: null
- `1795369085` **heartbeat**: null
- `1795369150` **heartbeat**: null
- `1795369192` **commented**: {"author": "engineering", "len": 2169}
- `1795369216` **heartbeat**: null
- `1795369274` **commented**: {"author": "engineering", "len": 1686}
- `1795369276` **heartbeat**: null
- `1795369285` **review_requested**: {"summary": "impl-1 on branch factory/t_18f19dba/impl-1 (commit c3faafe, tip 5d59f5b): docker-compose.yml now passes AIRFLOW_PROJ_DIR: ${AIRFLOW_PROJ_DIR} via the x-airflow-common env anchor to every airflow-* service; dags/jobtask.py dropped the hardcoded /run/media/... default and raises AirflowException naming the variable at DAG-parse time when unset/empty (TRITON_MODEL_STORE still derived from PROJECT_DIR", "implementer": "engineering", "reviewer": null}
- `1795369298` **claimed**: {"lock": "shantanu-ubuntu:284855", "expires": 1795370198, "run_id": 11, "source_status": "review"}
- `1795369298` **spawned**: {"pid": 583003, "started_at": "bffb47f0-8c10-4c03-81ec-d65431d434c6:16|6516566"}
- `1795369298` **owner_admitted**: {"db": "/home/hermes/.hermes/profiles/engineering/state.db", "session_id": "local-caddd1b2fe56701d5abc93c0b4994ac9b850f6a53de73efd103b6ec6ed81ad5b", "request_id": "kanban:[\"airflow-ml\",\"t_18f19dba\",11]", "pid": 284855, "birth": 52562.74}
- `1795369299` **worker_bound**: {"pid": 583046, "claim_lock": "shantanu-ubuntu:284855", "started_at": "bffb47f0-8c10-4c03-81ec-d65431d434c6:16|6516605"}
- `1795369301` **heartbeat**: null
- `1795369361` **heartbeat**: null
- `1795369419` **terminal_worker_reaped**: {"pid": 467138, "worker_started_at": "bffb47f0-8c10-4c03-81ec-d65431d434c6:16|6107141", "prev_pid": 467138, "host_local": true, "termination_attempted": true, "terminated": true, "sigkill": false}
- `1795369438` **heartbeat**: null
- `1795369527` **heartbeat**: null
- `1795369604` **heartbeat**: null
- `1795369687` **heartbeat**: null
- `1795369748` **heartbeat**: null
- `1795369808` **heartbeat**: null
- `1795369869` **heartbeat**: null
- `1795369932` **heartbeat**: null
- `1795370016` **heartbeat**: null
- `1795370079` **heartbeat**: null
- `1795370148` **heartbeat**: null
- `1795370233` **heartbeat**: null
- `1795370293` **heartbeat**: null
- `1795370306` **commented**: {"author": "engineering", "len": 3446}
- `1795370315` **blocked**: {"reason": "escalation: code review APPROVED on all code-level evidence (full record in comments: grep clean in dags/, compose v5.7.1 renders AIRFLOW_PROJ_DIR in env of all 9 airflow-* services incl. profile-gated flower/airflow-cli, parse-time guard verified by stub-import tests for unset/empty/set, .env untouched, EGM window exit 0 with on-branch provenance). Remaining acceptance item 3 (the staging proof this ticket exists for) is operator-gated: (1) operator removes the `service_env` workaround from .factory/deploy.yaml (operator-owned file — hermes cannot), (2) operator triggers the gpu_probe DAG after deploy. Once unblocked, hermes will run: `sudo factory-staging up airflow-ml --ref factory/t_18f19dba/impl-1`, verify the gpu_probe run succeeds, and `sudo factory-staging logs airflow-ml shim` for no refused creates — then approve via kanban_complete. Follow-up card t_d0cb9b72 filed for the same-class hardcoded fallback left in examples/detection/infer_cli.py (out of this card's scope).", "kind": "needs_input", "recurrences": 1, "source_status": "review"}
- `1795370324` **worker_result**: {"pid": 583046, "claim_lock": "shantanu-ubuntu:284855", "exit_code": 0, "last_output": "ment; follow-up card **`t_d0cb9b72`** created for the same-class hardcoded fallback still in `examples/detection/infer_cli.py:48-49` (out of this card's `dags/`-scoped acceptance, so it doesn't block); task blocked with the exact unblock path.\n\n**For the operator:** remove the `service_env` workaround from `.factory/deploy.yaml`, then trigger `gpu_probe` after deploy. On unblock, hermes runs `sudo factory-staging up airflow-ml --ref factory/t_18f19dba/impl-1` + the shim-log check, then approves."}

## Runs

- `` ****: {"id": 9, "profile": "engineering", "step_key": null, "status": "review", "outcome": "review_requested", "summary": "impl-1 on branch factory/t_18f19dba/impl-1 (commit c3faafe, tip 5d59f5b): docker-compose.yml now passes AIRFLOW_PROJ_DIR: ${AIRFLOW_PROJ_DIR} via the x-airflow-common env anchor to every airflow-* service; dags/jobtask.py dropped the hardcoded /run/media/... default and raises AirflowException naming the variable at DAG-parse time when unset/empty (TRITON_MODEL_STORE still derived from PROJECT_DIR); README marks AIRFLOW_PROJ_DIR required. Verified by me: grep -rn \"/run/media\" dags/ → clean; docker compose config (v5.7.1, branch checkout + operator .env) renders AIRFLOW_PROJ_DIR in the environment of all 8 default-profile airflow-* services (and profile-gated airflow-cli per YAML check); py_compile passes. Only the 3 source files changed; .env and .factory/ untouched. EGM review (window egm-review, harness claude) completed exit 0 — verdict text is in the retained tmux pane / transcript.log (dev-runner-owned; read commands in card comments) and the review branch factory/t_18f19dba/egm-review carries the provenance record. Operator-gated remainder: remove the service_env workaround from .factory/deploy.yaml, then factory-staging up --ref factory/t_18f19dba/impl-1 + gpu_probe + shim log check (hermes can run the staging up/logs steps once the workaround is removed).", "error": null, "metadata": {"artifacts_note": "no deliverable files; all outputs are git branches on the airflow-ml repo", "base_ref": "569bd02 (Initial commit / HEAD at dispatch)", "changed_files": ["docker-compose.yml", "dags/jobtask.py", "README.md"], "commit_impl": "c3faafe", "commit_record": {"egm_review": "9fc06e4", "impl_1": "5d59f5b"}, "dispatch_log_lines": ["2026-11-22 17:47:00 action=dispatch status=ok user=hermes ticket=t_18f19dba window=impl-1 window_id=@35 function=code_implementation harness=omp via=function_default executor=sandbox project=airflow-ml routing_sha=a1ce7f45d24
- `` ****: {"id": 11, "profile": "engineering", "step_key": null, "status": "blocked", "outcome": "blocked", "summary": "escalation: code review APPROVED on all code-level evidence (full record in comments: grep clean in dags/, compose v5.7.1 renders AIRFLOW_PROJ_DIR in env of all 9 airflow-* services incl. profile-gated flower/airflow-cli, parse-time guard verified by stub-import tests for unset/empty/set, .env untouched, EGM window exit 0 with on-branch provenance). Remaining acceptance item 3 (the staging proof this ticket exists for) is operator-gated: (1) operator removes the `service_env` workaround from .factory/deploy.yaml (operator-owned file — hermes cannot), (2) operator triggers the gpu_probe DAG after deploy. Once unblocked, hermes will run: `sudo factory-staging up airflow-ml --ref factory/t_18f19dba/impl-1`, verify the gpu_probe run succeeds, and `sudo factory-staging logs airflow-ml shim` for no refused creates — then approve via kanban_complete. Follow-up card t_d0cb9b72 filed for the same-class hardcoded fallback left in examples/detection/infer_cli.py (out of this card's scope).", "error": null, "metadata": null, "worker_pid": null, "started_at": 1795369298, "ended_at": 1795370315}

<details><summary>raw card JSON</summary>

```json
{
  "task": {
    "id": "t_18f19dba",
    "title": "Pass AIRFLOW_PROJ_DIR into containers; remove the hardcoded host path",
    "body": "factory:\n  function: code_implementation\n  base: HEAD\n\n## Problem\ndags/jobtask.py builds DockerOperator bind mounts from\n  PROJECT_DIR = os.environ.get(\"AIRFLOW_PROJ_DIR\", \"/run/media/shantanu/Volume/Projects/airflow-ml\")\nbut docker-compose.yml only uses AIRFLOW_PROJ_DIR for its own volume paths and never passes it into\nthe containers. Inside airflow-worker the variable is unset, so every job mounts the hardcoded path of\nthe operator's machine. That only works on this one host. In staging it made GPU jobs try to mount the\nlive project's dags/ and triton-models/ (refused by the staging policy).\n\n## Change\n1. docker-compose.yml: add `AIRFLOW_PROJ_DIR: ${AIRFLOW_PROJ_DIR}` to x-airflow-common.environment.\n2. dags/jobtask.py: remove the hardcoded default. If AIRFLOW_PROJ_DIR is unset, fail at DAG-parse time\n   with a clear message naming the variable.\n3. Keep TRITON_MODEL_STORE derived from AIRFLOW_PROJ_DIR, as today.\n4. Document AIRFLOW_PROJ_DIR in README/.env comments as required.\n\n## Acceptance\n- `grep -n \"/run/media\" dags/` finds nothing.\n- `docker compose config` shows AIRFLOW_PROJ_DIR in the environment of every airflow-* service.\n- Staging: `sudo factory-staging up airflow-ml --ref factory/<this card>/<window>` with the\n  `service_env` workaround removed from .factory/deploy.yaml (ask the operator), then trigger the\n  gpu_probe DAG: it succeeds, and `sudo factory-staging logs airflow-ml shim` shows no refused creates.\n- The operator's Docker instance keeps working (.env already sets AIRFLOW_PROJ_DIR).\n\n## Constraints\nCommit only source changes. Don't touch .env (gitignored, operator-owned).",
    "assignee": "engineering",
    "status": "blocked",
    "priority": 0,
    "tenant": null,
    "workspace_kind": "scratch",
    "workspace_path": "/home/hermes/.hermes/kanban/boards/airflow-ml/workspaces/t_18f19dba",
    "branch_name": null,
    "project_id": null,
    "created_by": "dashboard",
    "created_at": 1795365170,
    "started_at": 1795365204,
    "completed_at": null,
    "result": null,
    "skills": [],
    "max_runtime_seconds": null,
    "max_retries": null,
    "model_override": null,
    "provider_override": null,
    "session_id": null,
    "workflow_template_id": null,
    "current_step_key": null,
    "completion_contract": "local-only",
    "last_failure_error": null
  },
  "latest_summary": "escalation: code review APPROVED on all code-level evidence (full record in comments: grep clean in dags/, compose v5.7.1 renders AIRFLOW_PROJ_DIR in env of all 9 airflow-* services incl. profile-gated flower/airflow-cli, parse-time guard verified by stub-import tests for unset/empty/set, .env untouched, EGM window exit 0 with on-branch provenance). Remaining acceptance item 3 (the staging proof this ticket exists for) is operator-gated: (1) operator removes the `service_env` workaround from .factory/deploy.yaml (operator-owned file — hermes cannot), (2) operator triggers the gpu_probe DAG after deploy. Once unblocked, hermes will run: `sudo factory-staging up airflow-ml --ref factory/t_18f19dba/impl-1`, verify the gpu_probe run succeeds, and `sudo factory-staging logs airflow-ml shim` for no refused creates — then approve via kanban_complete. Follow-up card t_d0cb9b72 filed for the same-class hardcoded fallback left in examples/detection/infer_cli.py (out of this card's scope).",
  "parents": [],
  "children": [],
  "comments": [
    {
      "author": "engineering",
      "body": "**impl-1 complete** — branch `factory/t_18f19dba/impl-1`, tip `5d59f5b` (implementation commit `c3faafe`, record commit `5d59f5b`).\n\nDispatch log lines:\n- `2026-11-22 17:47:00 action=dispatch status=ok user=hermes ticket=t_18f19dba window=impl-1 window_id=@35 function=code_implementation harness=omp via=function_default mode=print executor=sandbox executor_via=policy_default isolation=container image=localhost/factory-runner@sha256:469e88d8… project=airflow-ml routing_sha=a1ce7f45d24409f3 prompt_sha=38f42190a3537469 workdir=/run/media/shantanu/Volume/Projects/airflow-ml meta=ok`\n- `2026-11-22 18:39:43 action=dispatch status=ok user=hermes ticket=t_18f19dba window=egm-review window_id=@37 function=egm_review harness=claude via=project_override mode=print executor=sandbox isolation=container … meta=ok`\n\nChanges on the branch (commit c3faafe):\n- `docker-compose.yml`: `AIRFLOW_PROJ_DIR: ${AIRFLOW_PROJ_DIR}` (no `:-` default) added to the `x-airflow-common` environment anchor.\n- `dags/jobtask.py`: hardcoded `/run/media/…` default removed; unset/empty `AIRFLOW_PROJ_DIR` now raises `AirflowException` at DAG-parse time naming the variable. `TRITON_MODEL_STORE` still derived from `PROJECT_DIR`.\n- `README.md`: `AIRFLOW_PROJ_DIR` marked required (no default) in the Configuration(.env) table.\n- Only those 3 files changed; `.env` and `.factory/` untouched.\n\nOrchestrator verification on the branch tip:\n- `grep -rn \"/run/media\" dags/` → no matches ✅\n- `docker compose config` (compose v5.7.1, branch checkout + operator .env) renders `AIRFLOW_PROJ_DIR: /run/media/shantanu/Volume/Projects/airflow-ml` in the environment of every default-profile airflow-* service (apiserver, conn-init, dag-processor, init, scheduler, triggerer, worker, flower); profile-gated `airflow-cli` also carries it (verified by YAML-anchor resolution) ✅\n- `python3 -m py_compile dags/jobtask.py` passes ✅\n\negm-review window dispatched and running; findings will be posted here. Remaining acceptance (staging `factory-staging up` + gpu_probe + shim logs, with the `service_env` workaround removed from `.factory/deploy.yaml`) is operator-gated per the card and will follow after review.",
      "created_at": 1795369192
    },
    {
      "author": "engineering",
      "body": "**egm-review complete** — window `egm-review` (harness claude via project_override, executor sandbox/container) exited 0.\n\n- Review branch: `factory/t_18f19dba/egm-review` (record commit `9fc06e4`, base `5d59f5b` of impl-1).\n- Dispatch log line: `2026-11-22 18:39:43 action=dispatch status=ok user=hermes ticket=t_18f19dba window=egm-review window_id=@37 function=egm_review harness=claude via=project_override mode=print executor=sandbox isolation=container image=localhost/factory-runner@sha256:469e88d8… project=airflow-ml routing_sha=a1ce7f45d24409f3 prompt_sha=1813930b8ace226e meta=ok`\n- Reviewer verdict/findings text lives in `transcript.log` (owner-only: dev-runner) and the retained tmux pane. Read with:\n  - `sudo -u dev-runner /usr/bin/tmux -S /var/run/tmux-factory/dev capture-pane -p -t t_18f19dba:egm-review | tail -100`\n  - or `sudo cat /srv/factory-jobs/t_18f19dba--egm-review/transcript.log`\n  (hermes has no sudo path for those; the tmux session/windows persist via remain-on-exit until `factory-clean`.)\n\nReview scope covered: parse-time failure semantics for Airflow 3.3.1, empty-vs-missing env interpolation, edge cases (other files assuming PROJECT_DIR set), diff hygiene.\n\n**Remaining operator-gated acceptance** (per card): remove the `service_env` workaround from `.factory/deploy.yaml` (operator-owned), then `sudo factory-staging up airflow-ml --ref factory/t_18f19dba/impl-1`, trigger the `gpu_probe` DAG, and check `sudo factory-staging logs airflow-ml shim` for refused creates. Once the workaround is removed, hermes can run the staging up/logs steps (they are in the sudo allowlist); triggering gpu_probe and the deploy.yaml edit remain on the operator.",
      "created_at": 1795369274
    },
    {
      "author": "engineering",
      "body": "**Review (round 1, lens: artifact) — code-level acceptance independently verified; staging proof still operator-gated.**\n\nIndependent re-verification on branch `factory/t_18f19dba/impl-1` (tip `5d59f5b`, impl commit `c3faafe`; fresh `git archive` checkout + operator `.env`, compose v5.7.1):\n\n- **Acceptance 1** `grep -rn \"/run/media\" dags/` → no matches on the branch tip. ✅ (repo-wide scan: remaining hits are `docs/detection-example/*.md` sample commands, `examples/detection/infer_cli.py:49` fallback, and `.factory` ticket records — all outside this card's acceptance scope.)\n- **Acceptance 2** `docker compose --env-file <operator .env> config --format json`: all 9 airflow-* services carry `AIRFLOW_PROJ_DIR=/run/media/shantanu/Volume/Projects/airflow-ml` in their rendered environment — 7 in the default-profile render (apiserver, conn-init, dag-processor, init, scheduler, triggerer, worker) plus profile-gated `flower` (profiles: [\"flower\"]) and `airflow-cli` (profiles: [\"debug\"]) via the `x-airflow-common` env anchor (line 43). Non-airflow services correctly don't carry it; zero interpolation warnings. ✅\n  - *Narrative nit (non-blocking):* the handoff listed `flower` among the default-profile services; it is actually profile-gated. No functional difference.\n- **Change 2 (parse-time guard)** — executed, not just read: stub-import tests of `dags/jobtask.py` (real file, stubbed `airflow` pkgs): `AIRFLOW_PROJ_DIR` unset → `AirflowException` at import/parse time naming the variable; set to `\"\"` → same failure (empty case covered by `if not PROJECT_DIR`); set to a path → clean import, `TRITON_MODEL_STORE` = `<dir>/triton-models` (change 3 preserved). `py_compile` passes. ✅\n- **Change 4** README table row now reads \"required — no default\". (The `.env`-comment half can't be committed — `.env` is gitignored/operator-owned per the card's own constraint; `.env` is confirmed untracked on the branch and untouched.) ✅\n- **Constraints** impl commit `c3faafe` touches exactly `README.md`, `dags/jobtask.py`, `docker-compose.yml`; `.env` untracked; `.factory/` deltas are the factory harness's own ticket-record commits (`5d59f5b`, `9fc06e4`, author \"Factory\"), not implementation changes. ✅\n- **EGM review** window `egm-review` provenance verified on-branch: base SHA `5d59f5b`, harness claude (project_override), exit 0, transcript SHA `be4b5386…` recorded in the ticket file. Findings text is owner-only (dev-runner) and not readable by hermes; this review does not rely on it.\n- **Operator instance (acceptance 4)**: operator `.env` sets `AIRFLOW_PROJ_DIR` (line 8); rendered config on the branch + that `.env` resolves the dags/config/triton-models volume binds to the operator's real path. No live redeploy performed (reviewer does not touch the running stack).\n\n**Remaining (acceptance 3, operator-gated):** remove the `service_env` workaround from `.factory/deploy.yaml` (operator-owned), `sudo factory-staging up airflow-ml --ref factory/t_18f19dba/impl-1` (hermes can run this + the logs step once unblocked), operator triggers `gpu_probe`, then verify DAG success and `sudo factory-staging logs airflow-ml shim` shows no refused creates.\n\n**Follow-up filed (out of scope for this card):** `examples/detection/infer_cli.py:48-49` keeps the same hardcoded `/run/media/…` fallback for `AIRFLOW_PROJ_DIR` — same defect class, outside the card's `dags/`-scoped acceptance; created a separate card so it doesn't block this one.",
      "created_at": 1795370306
    }
  ],
  "events": [
    {
      "kind": "created",
      "payload": {
        "assignee": "engineering",
        "status": "ready",
        "parents": [],
        "creator_task_id": null,
        "tenant": null,
        "workspace_kind": "scratch",
        "workspace_path": null,
        "branch_name": null,
        "project_id": null,
        "skills": null,
        "goal_mode": null,
        "model_override": null,
        "provider_override": null
      },
      "created_at": 1795365170,
      "run_id": null
    },
    {
      "kind": "edited",
      "payload": null,
      "created_at": 1795365184,
      "run_id": null
    },
    {
      "kind": "claimed",
      "payload": {
        "lock": "shantanu-ubuntu:284855",
        "expires": 1795366104,
        "run_id": 9
      },
      "created_at": 1795365204,
      "run_id": 9
    },
    {
      "kind": "spawned",
      "payload": {
        "pid": 467138,
        "started_at": "bffb47f0-8c10-4c03-81ec-d65431d434c6:16|6107141"
      },
      "created_at": 1795365204,
      "run_id": 9
    },
    {
      "kind": "owner_admitted",
      "payload": {
        "db": "/home/hermes/.hermes/profiles/engineering/state.db",
        "session_id": "local-9e197ed24ae86260c9c336e9d55594ebb5ef01e5dcaf08af6e93b61c6068965b",
        "request_id": "kanban:[\"airflow-ml\",\"t_18f19dba\",9]",
        "pid": 284855,
        "birth": 52562.74
      },
      "created_at": 1795365204,
      "run_id": 9
    },
    {
      "kind": "worker_bound",
      "payload": {
        "pid": 467179,
        "claim_lock": "shantanu-ubuntu:284855",
        "started_at": "bffb47f0-8c10-4c03-81ec-d65431d434c6:16|6107180"
      },
      "created_at": 1795365205,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795365206,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795365282,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795365345,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795365415,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795365475,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795365550,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795365632,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795365702,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795365762,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795365850,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795365910,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795365976,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795366050,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795366110,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": {
        "note": "impl-1 dispatched (omp/sandbox); waiting for .exit"
      },
      "created_at": 1795366160,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795366171,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795366231,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795366291,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795366351,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795366411,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795366471,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795366531,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795366591,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795366651,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795366731,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795366791,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795366858,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795366918,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795366978,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795367038,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795367098,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795367158,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795367218,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795367278,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795367338,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795367399,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": {
        "note": "impl-1 (omp) still running, ~18 min"
      },
      "created_at": 1795367399,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795367459,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795367519,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795367579,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795367639,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795367699,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795367760,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795367820,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795367880,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795367940,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795368000,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795368081,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795368143,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795368223,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795368300,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795368384,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795368464,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795368524,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795368599,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795368679,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795368740,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795368800,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795368873,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795368942,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795369002,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795369085,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795369150,
      "run_id": 9
    },
    {
      "kind": "commented",
      "payload": {
        "author": "engineering",
        "len": 2169
      },
      "created_at": 1795369192,
      "run_id": null
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795369216,
      "run_id": 9
    },
    {
      "kind": "commented",
      "payload": {
        "author": "engineering",
        "len": 1686
      },
      "created_at": 1795369274,
      "run_id": null
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795369276,
      "run_id": 9
    },
    {
      "kind": "review_requested",
      "payload": {
        "summary": "impl-1 on branch factory/t_18f19dba/impl-1 (commit c3faafe, tip 5d59f5b): docker-compose.yml now passes AIRFLOW_PROJ_DIR: ${AIRFLOW_PROJ_DIR} via the x-airflow-common env anchor to every airflow-* service; dags/jobtask.py dropped the hardcoded /run/media/... default and raises AirflowException naming the variable at DAG-parse time when unset/empty (TRITON_MODEL_STORE still derived from PROJECT_DIR",
        "implementer": "engineering",
        "reviewer": null
      },
      "created_at": 1795369285,
      "run_id": 9
    },
    {
      "kind": "claimed",
      "payload": {
        "lock": "shantanu-ubuntu:284855",
        "expires": 1795370198,
        "run_id": 11,
        "source_status": "review"
      },
      "created_at": 1795369298,
      "run_id": 11
    },
    {
      "kind": "spawned",
      "payload": {
        "pid": 583003,
        "started_at": "bffb47f0-8c10-4c03-81ec-d65431d434c6:16|6516566"
      },
      "created_at": 1795369298,
      "run_id": 11
    },
    {
      "kind": "owner_admitted",
      "payload": {
        "db": "/home/hermes/.hermes/profiles/engineering/state.db",
        "session_id": "local-caddd1b2fe56701d5abc93c0b4994ac9b850f6a53de73efd103b6ec6ed81ad5b",
        "request_id": "kanban:[\"airflow-ml\",\"t_18f19dba\",11]",
        "pid": 284855,
        "birth": 52562.74
      },
      "created_at": 1795369298,
      "run_id": 11
    },
    {
      "kind": "worker_bound",
      "payload": {
        "pid": 583046,
        "claim_lock": "shantanu-ubuntu:284855",
        "started_at": "bffb47f0-8c10-4c03-81ec-d65431d434c6:16|6516605"
      },
      "created_at": 1795369299,
      "run_id": 11
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795369301,
      "run_id": 11
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795369361,
      "run_id": 11
    },
    {
      "kind": "terminal_worker_reaped",
      "payload": {
        "pid": 467138,
        "worker_started_at": "bffb47f0-8c10-4c03-81ec-d65431d434c6:16|6107141",
        "prev_pid": 467138,
        "host_local": true,
        "termination_attempted": true,
        "terminated": true,
        "sigkill": false
      },
      "created_at": 1795369419,
      "run_id": 9
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795369438,
      "run_id": 11
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795369527,
      "run_id": 11
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795369604,
      "run_id": 11
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795369687,
      "run_id": 11
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795369748,
      "run_id": 11
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795369808,
      "run_id": 11
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795369869,
      "run_id": 11
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795369932,
      "run_id": 11
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795370016,
      "run_id": 11
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795370079,
      "run_id": 11
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795370148,
      "run_id": 11
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795370233,
      "run_id": 11
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795370293,
      "run_id": 11
    },
    {
      "kind": "commented",
      "payload": {
        "author": "engineering",
        "len": 3446
      },
      "created_at": 1795370306,
      "run_id": null
    },
    {
      "kind": "blocked",
      "payload": {
        "reason": "escalation: code review APPROVED on all code-level evidence (full record in comments: grep clean in dags/, compose v5.7.1 renders AIRFLOW_PROJ_DIR in env of all 9 airflow-* services incl. profile-gated flower/airflow-cli, parse-time guard verified by stub-import tests for unset/empty/set, .env untouched, EGM window exit 0 with on-branch provenance). Remaining acceptance item 3 (the staging proof this ticket exists for) is operator-gated: (1) operator removes the `service_env` workaround from .factory/deploy.yaml (operator-owned file — hermes cannot), (2) operator triggers the gpu_probe DAG after deploy. Once unblocked, hermes will run: `sudo factory-staging up airflow-ml --ref factory/t_18f19dba/impl-1`, verify the gpu_probe run succeeds, and `sudo factory-staging logs airflow-ml shim` for no refused creates — then approve via kanban_complete. Follow-up card t_d0cb9b72 filed for the same-class hardcoded fallback left in examples/detection/infer_cli.py (out of this card's scope).",
        "kind": "needs_input",
        "recurrences": 1,
        "source_status": "review"
      },
      "created_at": 1795370315,
      "run_id": 11
    },
    {
      "kind": "worker_result",
      "payload": {
        "pid": 583046,
        "claim_lock": "shantanu-ubuntu:284855",
        "exit_code": 0,
        "last_output": "ment; follow-up card **`t_d0cb9b72`** created for the same-class hardcoded fallback still in `examples/detection/infer_cli.py:48-49` (out of this card's `dags/`-scoped acceptance, so it doesn't block); task blocked with the exact unblock path.\n\n**For the operator:** remove the `service_env` workaround from `.factory/deploy.yaml`, then trigger `gpu_probe` after deploy. On unblock, hermes runs `sudo factory-staging up airflow-ml --ref factory/t_18f19dba/impl-1` + the shim-log check, then approves."
      },
      "created_at": 1795370324,
      "run_id": 11
    }
  ],
  "runs": [
    {
      "id": 9,
      "profile": "engineering",
      "step_key": null,
      "status": "review",
      "outcome": "review_requested",
      "summary": "impl-1 on branch factory/t_18f19dba/impl-1 (commit c3faafe, tip 5d59f5b): docker-compose.yml now passes AIRFLOW_PROJ_DIR: ${AIRFLOW_PROJ_DIR} via the x-airflow-common env anchor to every airflow-* service; dags/jobtask.py dropped the hardcoded /run/media/... default and raises AirflowException naming the variable at DAG-parse time when unset/empty (TRITON_MODEL_STORE still derived from PROJECT_DIR); README marks AIRFLOW_PROJ_DIR required. Verified by me: grep -rn \"/run/media\" dags/ → clean; docker compose config (v5.7.1, branch checkout + operator .env) renders AIRFLOW_PROJ_DIR in the environment of all 8 default-profile airflow-* services (and profile-gated airflow-cli per YAML check); py_compile passes. Only the 3 source files changed; .env and .factory/ untouched. EGM review (window egm-review, harness claude) completed exit 0 — verdict text is in the retained tmux pane / transcript.log (dev-runner-owned; read commands in card comments) and the review branch factory/t_18f19dba/egm-review carries the provenance record. Operator-gated remainder: remove the service_env workaround from .factory/deploy.yaml, then factory-staging up --ref factory/t_18f19dba/impl-1 + gpu_probe + shim log check (hermes can run the staging up/logs steps once the workaround is removed).",
      "error": null,
      "metadata": {
        "artifacts_note": "no deliverable files; all outputs are git branches on the airflow-ml repo",
        "base_ref": "569bd02 (Initial commit / HEAD at dispatch)",
        "changed_files": [
          "docker-compose.yml",
          "dags/jobtask.py",
          "README.md"
        ],
        "commit_impl": "c3faafe",
        "commit_record": {
          "egm_review": "9fc06e4",
          "impl_1": "5d59f5b"
        },
        "dispatch_log_lines": [
          "2026-11-22 17:47:00 action=dispatch status=ok user=hermes ticket=t_18f19dba window=impl-1 window_id=@35 function=code_implementation harness=omp via=function_default executor=sandbox project=airflow-ml routing_sha=a1ce7f45d24409f3 prompt_sha=38f42190a3537469 meta=ok",
          "2026-11-22 18:39:43 action=dispatch status=ok user=hermes ticket=t_18f19dba window=egm-review window_id=@37 function=egm_review harness=claude via=project_override executor=sandbox project=airflow-ml routing_sha=a1ce7f45d24409f3 prompt_sha=1813930b8ace226e meta=ok"
        ],
        "egm_findings_access": "transcript.log owner-only (dev-runner): sudo cat /srv/factory-jobs/t_18f19dba--egm-review/transcript.log; pane: sudo -u dev-runner tmux -S /var/run/tmux-factory/dev capture-pane -p -t t_18f19dba:egm-review",
        "egm_review_exit": "0",
        "operator_next_steps": [
          "remove service_env workaround from .factory/deploy.yaml (operator-owned)",
          "sudo factory-staging up airflow-ml --ref factory/t_18f19dba/impl-1",
          "trigger gpu_probe DAG",
          "sudo factory-staging logs airflow-ml shim — expect no refused creates"
        ],
        "review_branch": "factory/t_18f19dba/egm-review",
        "review_impl_branch": "factory/t_18f19dba/impl-1",
        "verifications": {
          "docker_compose_config": "PASS: rendered config shows AIRFLOW_PROJ_DIR=/run/media/shantanu/Volume/Projects/airflow-ml in env of all default-profile airflow-* services (compose v5.7.1 on branch checkout + operator .env); profile-gated airflow-cli also carries it per YAML-anchor check",
          "grep_run_media": "PASS: no matches in dags/ on branch tip",
          "py_compile": "PASS"
        },
        "worker_session_id": "local-9e197ed24ae86260c9c336e9d55594ebb5ef01e5dcaf08af6e93b61c6068965b"
      },
      "worker_pid": null,
      "started_at": 1795365204,
      "ended_at": 1795369285
    },
    {
      "id": 11,
      "profile": "engineering",
      "step_key": null,
      "status": "blocked",
      "outcome": "blocked",
      "summary": "escalation: code review APPROVED on all code-level evidence (full record in comments: grep clean in dags/, compose v5.7.1 renders AIRFLOW_PROJ_DIR in env of all 9 airflow-* services incl. profile-gated flower/airflow-cli, parse-time guard verified by stub-import tests for unset/empty/set, .env untouched, EGM window exit 0 with on-branch provenance). Remaining acceptance item 3 (the staging proof this ticket exists for) is operator-gated: (1) operator removes the `service_env` workaround from .factory/deploy.yaml (operator-owned file — hermes cannot), (2) operator triggers the gpu_probe DAG after deploy. Once unblocked, hermes will run: `sudo factory-staging up airflow-ml --ref factory/t_18f19dba/impl-1`, verify the gpu_probe run succeeds, and `sudo factory-staging logs airflow-ml shim` for no refused creates — then approve via kanban_complete. Follow-up card t_d0cb9b72 filed for the same-class hardcoded fallback left in examples/detection/infer_cli.py (out of this card's scope).",
      "error": null,
      "metadata": null,
      "worker_pid": null,
      "started_at": 1795369298,
      "ended_at": 1795370315
    }
  ]
}
```
</details>
