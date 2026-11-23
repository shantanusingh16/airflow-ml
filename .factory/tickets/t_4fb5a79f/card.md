# t_4fb5a79f — README polish: MLFLOW_ALLOWED_HOSTS doc nits from t_b64a74a1 review

Status: done · Assignee: engineering

## Body

factory:
  function: code_implementation
  base: HEAD

Optional documentation polish — two non-blocking README nits found in review of t_b64a74a1 (Make MLflow's allowed hosts configurable). Archive this card if the operator prefers to fold the fixes into the t_b64a74a1 merge instead.

Project: airflow-ml. Scope: README.md only — two wording fixes at the `MLFLOW_ALLOWED_HOSTS` doc locations (the "ML platform services" table `mlflow` row and the env-var table row, both around lines 125 and 225 as of branch factory/t_b64a74a1/impl-1):

1. State explicitly that setting `MLFLOW_ALLOWED_HOSTS` **replaces** the default rather than extending it. An operator who overrides with only the reverse-proxy host (e.g. `MLFLOW_ALLOWED_HOSTS=mlflow.example.com:8443`) drops `mlflow:5000`, which every job container needs via `MLFLOW_TRACKING_URI=http://mlflow:5000` → job containers get 403 from the MLflow server. Guidance should read: set the **full** list — keep `mlflow:5000` plus the exact `host[:port]` the UI is reached at (e.g. `mlflow:5000,mlflow.example.com:8443`).
2. Replace the change-history phrase "the previous pinned list" with the explicit entries (`mlflow:5000`, `localhost[:5000]`, `127.0.0.1[:5000]`) or a pointer to the full default value already shown in the env-var table.

Constraints:
- No changes to docker-compose.yml or any code — the behavior is final per t_b64a74a1; do not touch the `MLFLOW_ALLOWED_HOSTS` default or its character-for-character match between compose and README.
- Keep the existing "never set a bare `*`" warning intact.

Acceptance:
- README-only diff, both fixes present in both doc locations.
- The env-table default string still matches the compose default character-for-character.
- Dispatch a sandbox impl window; the change is prose — verification is diff review.

## Comments

- `1795386774` **engineering**: "**State (run 17, dependency-blocked):** dispatch attempt `factory-dispatch t_4fb5a79f impl-1 code_implementation /srv/software-factory/airflow-ml /srv/software-factory/.dispatch/t_4fb5a79f--impl-1.md` failed at front-matter validation (rc 2: `front matter base must be HEAD or factory/<this ticket>/<window>`) — cross-ticket base `factory/t_b64a74a1/egm-review` is not allowed, and `base: HEAD` is unusable until t_b664a74a1… correction: until **t_b64a74a1** is merged (HEAD 5cf2b9d has no MLFLOW_ALLOWED_HOSTS docs; the lines exist only at ~125/~225 on factory/t_b64a74a1/impl-1 and egm-review, README identical in both, egm-review adds only a .factory review-record file).\n\nNo job/session residue was created (validation failed pre-job; only the prompt file exists).\n\n**On resume (after t_b64a74a1 completes/merges):** verify `git -c safe.directory='*' -C /srv/software-factory/airflow-ml grep -c MLFLOW_ALLOWED_HOSTS HEAD -- README.md` ≥ 2, then dispatch from `/srv/software-factory` cwd: `sudo /usr/local/sbin/factory-dispatch t_4fb5a79f impl-1 code_implementation /srv/software-factory/airflow-ml /srv/software-factory/.dispatch/t_4fb5a79f--impl-1.md` (prompt is pre-staged with `base: HEAD`, both nits, README-only constraints, acceptance checks; it tells the harness to stop if the docs are absent). Afterwards: diff review (README-only, default string `mlflow:5000,localhost:5000,127.0.0.1:5000,localhost,127.0.0.1,localhost:*,127.0.0.1:*` char-for-char vs compose fallback, bare-`*` warning intact at both locations), post branch/SHA/log-line to the card, kanban_request_review. If the operator folded the fixes into the t_b64a74a1 merge, verify the two fixes are present at both locations and complete without dispatching."
- `1795387081` **engineering**: "**State (run 18, auto-resumed after t_b64a74a1 review completion):** t_b64a74a1 is approved but **not merged** — HEAD is still `5cf2b9d` (no `card export` commit for it), branch tip is still the reviewed `2578bb1`, and I verified neither nit was folded into the branch: both README locations (impl-1 lines 125 & 225) still read \"default = the previous pinned list…\" and carry no explicit \"replaces the default\" guidance.\n\n**Why I still can't dispatch:** the dispatcher only accepts `base: HEAD` or `factory/t_4fb5a79f/<window>` for this ticket, and HEAD's README contains **zero** `MLFLOW_ALLOWED_HOSTS` lines — a `base: HEAD` dispatch would hand the sandbox nothing to edit. The lines to polish exist only on `factory/t_b64a74a1/impl-1`.\n\n**What unblocks this card (operator):**\n1. **Merge `factory/t_b64a74a1/impl-1` into main** (with or without folding the two README fixes in) → this card auto-resumes:\n   - fixes folded into the merge → I verify both fixes present at both locations and complete **without dispatching**;\n   - fixes not folded → I dispatch the pre-staged `impl-1` prompt (already at `/srv/software-factory/.dispatch/t_4fb5a79f--impl-1.md`, `base: HEAD`, both nits + README-only constraints + acceptance checks), then diff review → `kanban_request_review`.\n2. Or explicitly **archive this card** if the fixes are being folded into the merge (per the card body).\n\nNo job/session residue; only the prompt file exists."
- `1795387279` **dashboard**: "Also include the t_18f19dba review nits (now on master): ▎ (1) README says AIRFLOW_PROJ_DIR is \"required — no default\", but compose's own service mounts still fall back to ${AIRFLOW_PROJ_DIR:-.}. Reword: required for job containers; compose's own mounts fall back to .. ▎ (2) dags/jobtask.py:20, the docker-compose.yml:40 comment and README.md:208 say job containers mount dags/, config/ and triton-models/. _job_mounts() mounts only dags/ and triton-models/. Drop config/. ▎ Comments and docs only, no behaviour change."
- `1795387783` **engineering**: "**impl-1 dispatched, exit 0, diff-reviewed — ready for review.**\n\n- Branch: `factory/t_4fb5a79f/impl-1`, impl commit **`e6ccaa0`** (record commit `52da34e`), base = `325aa68` (t_b64a74a1 merge tip = current main).\n- Dispatch log: `2026-11-22 23:44:16 action=dispatch status=ok user=hermes ticket=t_4fb5a79f window=impl-1 window_id=@15 function=code_implementation harness=omp via=function_default mode=print … project=airflow-ml … meta=ok`\n- Files: `README.md`, `dags/jobtask.py` (one message string), `docker-compose.yml` (one comment line) — +5/−5, prose only.\n\n**My verification (independent of the harness report):**\n1. Both MLFLOW fixes at **both** locations (services-table `mlflow` row L125 + env-table row L225): \"replaces the default list rather than extending it\", full-list guidance (`mlflow:5000,mlflow.example.com:8443`), the bare-proxy-host form only inside the 403 warning, \"previous pinned list\" → explicit `mlflow:5000`, `localhost:5000`, `127.0.0.1:5000` + `localhost:*`/`127.0.0.1:*`.\n2. Env-table default cell vs compose `${MLFLOW_ALLOWED_HOSTS:-…}` fallback (compose L318): **byte-identical** (`mlflow:5000,localhost:5000,127.0.0.1:5000,localhost,127.0.0.1,localhost:*,127.0.0.1:*`); compose diff = the single comment line only.\n3. Bare-`*` warning intact verbatim at both locations; all three edited rows keep 3 balanced columns.\n4. Fold-in (per dashboard comment): Nit A (AIRFLOW_PROJ_DIR row → \"required for job containers (unset/empty → job tasks fail fast — dags/jobtask.py raises); compose's own airflow-service mounts fall back to `.`\") and Nit B (`config/` dropped from the job-mount list in jobtask.py's exception message, the compose comment L40, and README L208) — `grep -c \"dags/, config/\"` = 0 in all three files.\n5. `docker compose config` rc 0 on the branch tree (host-side, operator .env) — no rendering change; `ast.parse` on jobtask.py OK.\n\nHarness note: `docker compose config` wasn't runnable in the sandbox (no docker binary); covered b

## Events

- `1795386534` **created**: {"assignee": "engineering", "status": "ready", "parents": [], "creator_task_id": "t_b64a74a1", "tenant": null, "workspace_kind": "scratch", "workspace_path": null, "branch_name": null, "project_id": null, "skills": null, "goal_mode": null, "model_override": null, "provider_override": null}
- `1795386589` **claimed**: {"lock": "shantanu-ubuntu:817106", "expires": 1795387489, "run_id": 17}
- `1795386589` **spawned**: {"pid": 1135049, "started_at": "bffb47f0-8c10-4c03-81ec-d65431d434c6:16|8245687"}
- `1795386590` **owner_admitted**: {"db": "/home/hermes/.hermes/profiles/engineering/state.db", "session_id": "local-789f4871aea5397ff44d07ca626a2eb09c6e51e61b5df562d376ebc0d5c8ca73", "request_id": "kanban:[\"airflow-ml\",\"t_4fb5a79f\",17]", "pid": 817106, "birth": 73409.83}
- `1795386590` **worker_bound**: {"pid": 1135091, "claim_lock": "shantanu-ubuntu:817106", "started_at": "bffb47f0-8c10-4c03-81ec-d65431d434c6:16|8245740"}
- `1795386592` **heartbeat**: null
- `1795386652` **heartbeat**: null
- `1795386717` **heartbeat**: null
- `1795386762` **linked**: {"parent": "t_b64a74a1", "child": "t_4fb5a79f"}
- `1795386765` **dependency_wait**: {"reason": "Cannot dispatch yet: the README lines to polish exist only on t_b64a74a1's branches (factory/t_b64a74a1/impl-1, tip 2578bb1) — t_b64a74a1 is not merged into main (HEAD=5cf2b9d has no MLFLOW_ALLOWED_HOSTS docs), and the dispatcher only accepts base HEAD or factory/t_4fb5a79f/<window> for this ticket (cross-ticket bases rejected: 'front matter base must be HEAD or factory/<this ticket>/<window>'). This card is now parent-linked to t_b64a74a1 and will auto-resume when it completes; the impl prompt is pre-staged at /srv/software-factory/.dispatch/t_4fb5a79f--impl-1.md (base: HEAD, both nits, README-only constraints) and is ready to dispatch on resume. If you fold the two README fixes into the t_b64a74a1 merge instead, just archive this card. Note t_b64a74a1 itself is blocked on your staging acceptance (GPU VRAM guard or --force) — merging it is what unblocks both.", "kind": "dependency", "source_status": "ready"}
- `1795386774` **commented**: {"author": "engineering", "len": 1732}
- `1795386782` **worker_result**: {"pid": 1135091, "claim_lock": "shantanu-ubuntu:817106", "exit_code": 0, "last_output": " → it's now `todo` and will **auto-resume** when t_b64a74a1 completes.\n   - Left a handoff comment with the exact re-dispatch command and acceptance checks so the resumed run acts immediately.\n\n**Operator options (both already on the card):** merge t_b64a74a1 as-is → this card re-dispatches against the updated HEAD automatically; or fold the two README fixes into that merge and archive this card. Unblocking t_b64a74a1 (free ≥8 GB VRAM or `--force`, per its block note) is what moves both forward."}
- `1795386987` **promoted**: null
- `1795387011` **claimed**: {"lock": "shantanu-ubuntu:817106", "expires": 1795387911, "run_id": 19}
- `1795387011` **spawned**: {"pid": 1147728, "started_at": "bffb47f0-8c10-4c03-81ec-d65431d434c6:16|8287849"}
- `1795387011` **owner_admitted**: {"db": "/home/hermes/.hermes/profiles/engineering/state.db", "session_id": "local-50c208ecf4b7b255ef0c169b280ff09f8fd9fde6facaab9549878212c2e6e347", "request_id": "kanban:[\"airflow-ml\",\"t_4fb5a79f\",19]", "pid": 817106, "birth": 73409.83}
- `1795387012` **worker_bound**: {"pid": 1147783, "claim_lock": "shantanu-ubuntu:817106", "started_at": "bffb47f0-8c10-4c03-81ec-d65431d434c6:16|8287885"}
- `1795387013` **heartbeat**: null
- `1795387073` **heartbeat**: null
- `1795387081` **commented**: {"author": "engineering", "len": 1435}
- `1795387087` **blocked**: {"reason": "Waiting on operator: merge factory/t_b64a74a1/impl-1 into main (t_4fb5a74a1 is approved but HEAD is still 5cf2b9d with no MLFLOW_ALLOWED_HOSTS docs, and cross-ticket bases are rejected by the dispatcher), or archive this card if the two README nits are folded into that merge. On resume: if nits are folded, verify and complete without dispatch; otherwise dispatch the pre-staged impl-1 prompt (base: HEAD).", "kind": "needs_input", "recurrences": 1, "source_status": "ready"}
- `1795387091` **worker_result**: {"pid": 1147783, "claim_lock": "shantanu-ubuntu:817106", "exit_code": 0, "last_output": "hat I did**\n- Posted the full state + unblock options as a card comment (comment 19).\n- `kanban_block(kind=needs_input)`: the operator needs to either **(1)** merge `factory/t_b64a74a1/impl-1` into main — with or without folding the two README fixes in — which auto-resumes this card (I'll verify-and-close if folded, or dispatch the pre-staged `impl-1` window if not), or **(2)** archive this card if the fixes are folded into the merge.\n\nNo job or session residue was created (no dispatch was run)."}
- `1795387279` **commented**: {"author": "dashboard", "len": 520}
- `1795387288` **unblocked**: null
- `1795387344` **claimed**: {"lock": "shantanu-ubuntu:1154856", "expires": 1795388244, "run_id": 20}
- `1795387344` **spawned**: {"pid": 1166224, "started_at": "bffb47f0-8c10-4c03-81ec-d65431d434c6:16|8321148"}
- `1795387344` **owner_admitted**: {"db": "/home/hermes/.hermes/profiles/engineering/state.db", "session_id": "local-2a0f5c6c4bac86176317574646f8a5df6869e30f19046f4a830ccde62e85f934", "request_id": "kanban:[\"airflow-ml\",\"t_4fb5a79f\",20]", "pid": 1154856, "birth": 83021.14}
- `1795387345` **worker_bound**: {"pid": 1166327, "claim_lock": "shantanu-ubuntu:1154856", "started_at": "bffb47f0-8c10-4c03-81ec-d65431d434c6:16|8321240"}
- `1795387347` **heartbeat**: null
- `1795387407` **heartbeat**: null
- `1795387469` **heartbeat**: null
- `1795387529` **heartbeat**: null
- `1795387590` **heartbeat**: null
- `1795387650` **heartbeat**: null
- `1795387710` **heartbeat**: null
- `1795387770` **heartbeat**: null
- `1795387783` **commented**: {"author": "engineering", "len": 2110}
- `1795387789` **review_requested**: {"summary": "README polish (t_4fb5a79f) implemented via sandbox impl-1 window and diff-reviewed by me: both MLFLOW_ALLOWED_HOSTS nits at both doc locations (override replaces default — full-list guidance with the 403 warning; \"previous pinned list\" spelled out explicitly), plus the two folded-in t_18f19dba nits requested on the card (AIRFLOW_PROJ_DIR \"required for job containers\" reword; config/ dropped from t", "implementer": "engineering", "reviewer": null}
- `1795387816` **worker_result**: {"pid": 1166327, "claim_lock": "shantanu-ubuntu:1154856", "exit_code": 0, "last_output": "old-in nits: AIRFLOW_PROJ_DIR row now says \"required for job containers …; compose's own airflow-service mounts fall back to `.`\", and `config/` is dropped from the job-mount list in all three places (zero `dags/, config/` residues).\n\nHandoff (branch, tip SHA, dispatch log line, verification) is posted on the card; `kanban_request_review` moved it to review (run 20). If review approves, the operator merges `factory/t_4fb5a79f/impl-1` and the ticket can be cleaned with `factory-clean t_4fb5a79f`."}
- `1795387826` **claimed**: {"lock": "shantanu-ubuntu:1154856", "expires": 1795388726, "run_id": 22, "source_status": "review"}
- `1795387826` **spawned**: {"pid": 1180408, "started_at": "bffb47f0-8c10-4c03-81ec-d65431d434c6:16|8369315"}
- `1795387826` **owner_admitted**: {"db": "/home/hermes/.hermes/profiles/engineering/state.db", "session_id": "local-09d9a4313e6ce9d42b22eddabc018d3a4decbd3837ac273700c638ef2d58b4b3", "request_id": "kanban:[\"airflow-ml\",\"t_4fb5a79f\",22]", "pid": 1154856, "birth": 83021.14}
- `1795387826` **worker_bound**: {"pid": 1180452, "claim_lock": "shantanu-ubuntu:1154856", "started_at": "bffb47f0-8c10-4c03-81ec-d65431d434c6:16|8369363"}
- `1795387828` **heartbeat**: null
- `1795387888` **heartbeat**: null
- `1795387948` **heartbeat**: null
- `1795387968` **completed**: {"result_len": 0, "summary": "Reviewed and approved (round 1, artifact lens — cold diff read of factory/t_4fb5a79f/impl-1, commit e6ccaa0 on base 325aa68, fully independent of the handoff narrative). Both MLFLOW_ALLOWED_HOSTS nits verified present at both doc locations: \"replaces the default list rather than extending it\" with full-list guidance (`mlflow:5000,mlflow.example.com:8443`) and the 403 warning explaining the MLFLOW_"}
- `1795387989` **worker_result**: {"pid": 1180452, "claim_lock": "shantanu-ubuntu:1154856", "exit_code": 0, "last_output": " base whose rendering was already validated in that review; bare-`*` warning intact verbatim at both spots.\n4. **Fold-in nits** (dashboard's card comment): both landed exactly as specified; diff is +5/−5 with the only non-README lines being the requested `jobtask.py` message string and compose comment line — no behaviour change, so the card's hard constraints hold.\n\nThe card is now `done`; the operator can merge `factory/t_4fb5a79f/impl-1` and run `factory-clean t_4fb5a79f` when the merge lands."}

## Runs

- `` ****: {"id": 17, "profile": "engineering", "step_key": null, "status": "blocked", "outcome": "blocked", "summary": "Cannot dispatch yet: the README lines to polish exist only on t_b64a74a1's branches (factory/t_b64a74a1/impl-1, tip 2578bb1) — t_b64a74a1 is not merged into main (HEAD=5cf2b9d has no MLFLOW_ALLOWED_HOSTS docs), and the dispatcher only accepts base HEAD or factory/t_4fb5a79f/<window> for this ticket (cross-ticket bases rejected: 'front matter base must be HEAD or factory/<this ticket>/<window>'). This card is now parent-linked to t_b64a74a1 and will auto-resume when it completes; the impl prompt is pre-staged at /srv/software-factory/.dispatch/t_4fb5a79f--impl-1.md (base: HEAD, both nits, README-only constraints) and is ready to dispatch on resume. If you fold the two README fixes into the t_b64a74a1 merge instead, just archive this card. Note t_b64a74a1 itself is blocked on your staging acceptance (GPU VRAM guard or --force) — merging it is what unblocks both.", "error": null, "metadata": null, "worker_pid": null, "started_at": 1795386589, "ended_at": 1795386765}
- `` ****: {"id": 19, "profile": "engineering", "step_key": null, "status": "blocked", "outcome": "blocked", "summary": "Waiting on operator: merge factory/t_b64a74a1/impl-1 into main (t_4fb5a74a1 is approved but HEAD is still 5cf2b9d with no MLFLOW_ALLOWED_HOSTS docs, and cross-ticket bases are rejected by the dispatcher), or archive this card if the two README nits are folded into that merge. On resume: if nits are folded, verify and complete without dispatch; otherwise dispatch the pre-staged impl-1 prompt (base: HEAD).", "error": null, "metadata": null, "worker_pid": null, "started_at": 1795387011, "ended_at": 1795387087}
- `` ****: {"id": 20, "profile": "engineering", "step_key": null, "status": "review", "outcome": "review_requested", "summary": "README polish (t_4fb5a79f) implemented via sandbox impl-1 window and diff-reviewed by me: both MLFLOW_ALLOWED_HOSTS nits at both doc locations (override replaces default — full-list guidance with the 403 warning; \"previous pinned list\" spelled out explicitly), plus the two folded-in t_18f19dba nits requested on the card (AIRFLOW_PROJ_DIR \"required for job containers\" reword; config/ dropped from the job-mount list in jobtask.py message, compose comment, README row). Compose fallback vs env-table default byte-identical; bare-* warning intact; docker compose config rc 0 on the branch tree; diff is prose/comment-only (+5/−5). Branch factory/t_4fb5a79f/impl-1, commit e6ccaa0, base 325aa68.", "error": null, "metadata": {"base": "325aa68", "branch": "factory/t_4fb5a79f/impl-1", "checks": ["both MLFLOW fixes at both doc locations (README L125 services row + L225 env row)", "env-table default byte-identical to compose ${MLFLOW_ALLOWED_HOSTS:-...} fallback", "bare-* warning intact at both locations", "fold-in nits (dashboard request): AIRFLOW_PROJ_DIR wording + config/ dropped from job-mount list in 3 places", "docker compose config rc 0 on branch tree (host-side, operator .env); ast.parse jobtask.py OK", "diff = README.md + one jobtask.py message string + one compose comment line, +5/-5"], "commit": "e6ccaa0", "folded_in": "t_18f19dba nits A+B per dashboard card comment", "log_line": "2026-11-22 23:44:16 action=dispatch status=ok ticket=t_4fb5a79f window=impl-1 function=code_implementation harness=omp project=airflow-ml", "result_md": "/srv/factory-artifacts/t_4fb5a79f/impl-1/result.md", "tip_sha": "e6ccaa043bca74b556de03c46cbc48bb84c5207b", "worker_session_id": "local-2a0f5c6c4bac86176317574646f8a5df6869e30f19046f4a830ccde62e85f934"}, "worker_pid": null, "started_at": 1795387344, "ended_at": 1795387789}
- `` ****: {"id": 22, "profile": "engineering", "step_key": null, "status": "done", "outcome": "completed", "summary": "Reviewed and approved (round 1, artifact lens — cold diff read of factory/t_4fb5a79f/impl-1, commit e6ccaa0 on base 325aa68, fully independent of the handoff narrative). Both MLFLOW_ALLOWED_HOSTS nits verified present at both doc locations: \"replaces the default list rather than extending it\" with full-list guidance (`mlflow:5000,mlflow.example.com:8443`) and the 403 warning explaining the MLFLOW_TRACKING_URI drop, and \"the previous pinned list\" replaced with the explicit entries at both the services-table row and the env-table row (old phrase confirmed present in base, absent on branch). Env-table default cell is char-for-char identical to the compose `${MLFLOW_ALLOWED_HOSTS:-…}` fallback, which is unchanged from the t_b64a74a1 base already verified in its own review; the bare-`*` warning is intact verbatim at both locations and no bare `*` appears in any default/example. The two folded-in t_18f19dba nits from the dashboard card comment landed exactly as specified (AIRFLOW_PROJ_DIR \"required for job containers\" reword; `config/` dropped from the job-mount list in jobtask.py's message, the compose comment, and the README row, with zero residues) — the only non-README lines are that requested fold-in (one string literal, one comment line), a documented spec amendment, so the card's hard constraints (no MLFLOW default change, no behaviour change) hold. Ready for the operator to merge factory/t_4fb5a79f/impl-1.", "error": null, "metadata": {"base": "325aa68 (master HEAD = t_b64a74a1 merge)", "branch": "factory/t_4fb5a79f/impl-1", "commit": "e6ccaa0", "review_outcome": "approved", "review_round": "1 (artifact lens: cold diff read, independent of handoff narrative)", "reviewer_checks": ["cold-read git diff 325aa68..e6ccaa0: exactly 3 files, +5/-5, all prose/comments", "fix 1 (replaces-not-extends + full-list guidance `mlflow:5000,mlflow.example.com:8443` + 4

<details><summary>raw card JSON</summary>

```json
{
  "task": {
    "id": "t_4fb5a79f",
    "title": "README polish: MLFLOW_ALLOWED_HOSTS doc nits from t_b64a74a1 review",
    "body": "factory:\n  function: code_implementation\n  base: HEAD\n\nOptional documentation polish — two non-blocking README nits found in review of t_b64a74a1 (Make MLflow's allowed hosts configurable). Archive this card if the operator prefers to fold the fixes into the t_b64a74a1 merge instead.\n\nProject: airflow-ml. Scope: README.md only — two wording fixes at the `MLFLOW_ALLOWED_HOSTS` doc locations (the \"ML platform services\" table `mlflow` row and the env-var table row, both around lines 125 and 225 as of branch factory/t_b64a74a1/impl-1):\n\n1. State explicitly that setting `MLFLOW_ALLOWED_HOSTS` **replaces** the default rather than extending it. An operator who overrides with only the reverse-proxy host (e.g. `MLFLOW_ALLOWED_HOSTS=mlflow.example.com:8443`) drops `mlflow:5000`, which every job container needs via `MLFLOW_TRACKING_URI=http://mlflow:5000` → job containers get 403 from the MLflow server. Guidance should read: set the **full** list — keep `mlflow:5000` plus the exact `host[:port]` the UI is reached at (e.g. `mlflow:5000,mlflow.example.com:8443`).\n2. Replace the change-history phrase \"the previous pinned list\" with the explicit entries (`mlflow:5000`, `localhost[:5000]`, `127.0.0.1[:5000]`) or a pointer to the full default value already shown in the env-var table.\n\nConstraints:\n- No changes to docker-compose.yml or any code — the behavior is final per t_b64a74a1; do not touch the `MLFLOW_ALLOWED_HOSTS` default or its character-for-character match between compose and README.\n- Keep the existing \"never set a bare `*`\" warning intact.\n\nAcceptance:\n- README-only diff, both fixes present in both doc locations.\n- The env-table default string still matches the compose default character-for-character.\n- Dispatch a sandbox impl window; the change is prose — verification is diff review.",
    "assignee": "engineering",
    "status": "done",
    "priority": 1,
    "tenant": null,
    "workspace_kind": "scratch",
    "workspace_path": "/home/hermes/.hermes/kanban/boards/airflow-ml/workspaces/t_4fb5a79f",
    "branch_name": null,
    "project_id": null,
    "created_by": "engineering",
    "created_at": 1795386534,
    "started_at": 1795386589,
    "completed_at": 1795387968,
    "result": null,
    "skills": [],
    "max_runtime_seconds": null,
    "max_retries": null,
    "model_override": null,
    "provider_override": null,
    "session_id": "local-c6ff392147504a3c615bb7ff6fbdc66243cc483fedca4a10b326dff9392d7f90",
    "workflow_template_id": null,
    "current_step_key": null,
    "completion_contract": "local-only",
    "last_failure_error": null
  },
  "latest_summary": "Reviewed and approved (round 1, artifact lens — cold diff read of factory/t_4fb5a79f/impl-1, commit e6ccaa0 on base 325aa68, fully independent of the handoff narrative). Both MLFLOW_ALLOWED_HOSTS nits verified present at both doc locations: \"replaces the default list rather than extending it\" with full-list guidance (`mlflow:5000,mlflow.example.com:8443`) and the 403 warning explaining the MLFLOW_TRACKING_URI drop, and \"the previous pinned list\" replaced with the explicit entries at both the services-table row and the env-table row (old phrase confirmed present in base, absent on branch). Env-table default cell is char-for-char identical to the compose `${MLFLOW_ALLOWED_HOSTS:-…}` fallback, which is unchanged from the t_b64a74a1 base already verified in its own review; the bare-`*` warning is intact verbatim at both locations and no bare `*` appears in any default/example. The two folded-in t_18f19dba nits from the dashboard card comment landed exactly as specified (AIRFLOW_PROJ_DIR \"required for job containers\" reword; `config/` dropped from the job-mount list in jobtask.py's message, the compose comment, and the README row, with zero residues) — the only non-README lines are that requested fold-in (one string literal, one comment line), a documented spec amendment, so the card's hard constraints (no MLFLOW default change, no behaviour change) hold. Ready for the operator to merge factory/t_4fb5a79f/impl-1.",
  "parents": [
    "t_b64a74a1"
  ],
  "children": [],
  "comments": [
    {
      "author": "engineering",
      "body": "**State (run 17, dependency-blocked):** dispatch attempt `factory-dispatch t_4fb5a79f impl-1 code_implementation /srv/software-factory/airflow-ml /srv/software-factory/.dispatch/t_4fb5a79f--impl-1.md` failed at front-matter validation (rc 2: `front matter base must be HEAD or factory/<this ticket>/<window>`) — cross-ticket base `factory/t_b64a74a1/egm-review` is not allowed, and `base: HEAD` is unusable until t_b664a74a1… correction: until **t_b64a74a1** is merged (HEAD 5cf2b9d has no MLFLOW_ALLOWED_HOSTS docs; the lines exist only at ~125/~225 on factory/t_b64a74a1/impl-1 and egm-review, README identical in both, egm-review adds only a .factory review-record file).\n\nNo job/session residue was created (validation failed pre-job; only the prompt file exists).\n\n**On resume (after t_b64a74a1 completes/merges):** verify `git -c safe.directory='*' -C /srv/software-factory/airflow-ml grep -c MLFLOW_ALLOWED_HOSTS HEAD -- README.md` ≥ 2, then dispatch from `/srv/software-factory` cwd: `sudo /usr/local/sbin/factory-dispatch t_4fb5a79f impl-1 code_implementation /srv/software-factory/airflow-ml /srv/software-factory/.dispatch/t_4fb5a79f--impl-1.md` (prompt is pre-staged with `base: HEAD`, both nits, README-only constraints, acceptance checks; it tells the harness to stop if the docs are absent). Afterwards: diff review (README-only, default string `mlflow:5000,localhost:5000,127.0.0.1:5000,localhost,127.0.0.1,localhost:*,127.0.0.1:*` char-for-char vs compose fallback, bare-`*` warning intact at both locations), post branch/SHA/log-line to the card, kanban_request_review. If the operator folded the fixes into the t_b64a74a1 merge, verify the two fixes are present at both locations and complete without dispatching.",
      "created_at": 1795386774
    },
    {
      "author": "engineering",
      "body": "**State (run 18, auto-resumed after t_b64a74a1 review completion):** t_b64a74a1 is approved but **not merged** — HEAD is still `5cf2b9d` (no `card export` commit for it), branch tip is still the reviewed `2578bb1`, and I verified neither nit was folded into the branch: both README locations (impl-1 lines 125 & 225) still read \"default = the previous pinned list…\" and carry no explicit \"replaces the default\" guidance.\n\n**Why I still can't dispatch:** the dispatcher only accepts `base: HEAD` or `factory/t_4fb5a79f/<window>` for this ticket, and HEAD's README contains **zero** `MLFLOW_ALLOWED_HOSTS` lines — a `base: HEAD` dispatch would hand the sandbox nothing to edit. The lines to polish exist only on `factory/t_b64a74a1/impl-1`.\n\n**What unblocks this card (operator):**\n1. **Merge `factory/t_b64a74a1/impl-1` into main** (with or without folding the two README fixes in) → this card auto-resumes:\n   - fixes folded into the merge → I verify both fixes present at both locations and complete **without dispatching**;\n   - fixes not folded → I dispatch the pre-staged `impl-1` prompt (already at `/srv/software-factory/.dispatch/t_4fb5a79f--impl-1.md`, `base: HEAD`, both nits + README-only constraints + acceptance checks), then diff review → `kanban_request_review`.\n2. Or explicitly **archive this card** if the fixes are being folded into the merge (per the card body).\n\nNo job/session residue; only the prompt file exists.",
      "created_at": 1795387081
    },
    {
      "author": "dashboard",
      "body": "Also include the t_18f19dba review nits (now on master): ▎ (1) README says AIRFLOW_PROJ_DIR is \"required — no default\", but compose's own service mounts still fall back to ${AIRFLOW_PROJ_DIR:-.}. Reword: required for job containers; compose's own mounts fall back to .. ▎ (2) dags/jobtask.py:20, the docker-compose.yml:40 comment and README.md:208 say job containers mount dags/, config/ and triton-models/. _job_mounts() mounts only dags/ and triton-models/. Drop config/. ▎ Comments and docs only, no behaviour change.",
      "created_at": 1795387279
    },
    {
      "author": "engineering",
      "body": "**impl-1 dispatched, exit 0, diff-reviewed — ready for review.**\n\n- Branch: `factory/t_4fb5a79f/impl-1`, impl commit **`e6ccaa0`** (record commit `52da34e`), base = `325aa68` (t_b64a74a1 merge tip = current main).\n- Dispatch log: `2026-11-22 23:44:16 action=dispatch status=ok user=hermes ticket=t_4fb5a79f window=impl-1 window_id=@15 function=code_implementation harness=omp via=function_default mode=print … project=airflow-ml … meta=ok`\n- Files: `README.md`, `dags/jobtask.py` (one message string), `docker-compose.yml` (one comment line) — +5/−5, prose only.\n\n**My verification (independent of the harness report):**\n1. Both MLFLOW fixes at **both** locations (services-table `mlflow` row L125 + env-table row L225): \"replaces the default list rather than extending it\", full-list guidance (`mlflow:5000,mlflow.example.com:8443`), the bare-proxy-host form only inside the 403 warning, \"previous pinned list\" → explicit `mlflow:5000`, `localhost:5000`, `127.0.0.1:5000` + `localhost:*`/`127.0.0.1:*`.\n2. Env-table default cell vs compose `${MLFLOW_ALLOWED_HOSTS:-…}` fallback (compose L318): **byte-identical** (`mlflow:5000,localhost:5000,127.0.0.1:5000,localhost,127.0.0.1,localhost:*,127.0.0.1:*`); compose diff = the single comment line only.\n3. Bare-`*` warning intact verbatim at both locations; all three edited rows keep 3 balanced columns.\n4. Fold-in (per dashboard comment): Nit A (AIRFLOW_PROJ_DIR row → \"required for job containers (unset/empty → job tasks fail fast — dags/jobtask.py raises); compose's own airflow-service mounts fall back to `.`\") and Nit B (`config/` dropped from the job-mount list in jobtask.py's exception message, the compose comment L40, and README L208) — `grep -c \"dags/, config/\"` = 0 in all three files.\n5. `docker compose config` rc 0 on the branch tree (host-side, operator .env) — no rendering change; `ast.parse` on jobtask.py OK.\n\nHarness note: `docker compose config` wasn't runnable in the sandbox (no docker binary); covered by the host-side check above. Transcript for the record: `sudo cat /srv/factory-jobs/t_4fb5a79f--impl-1/transcript.log` (owner-only).",
      "created_at": 1795387783
    }
  ],
  "events": [
    {
      "kind": "created",
      "payload": {
        "assignee": "engineering",
        "status": "ready",
        "parents": [],
        "creator_task_id": "t_b64a74a1",
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
      "created_at": 1795386534,
      "run_id": null
    },
    {
      "kind": "claimed",
      "payload": {
        "lock": "shantanu-ubuntu:817106",
        "expires": 1795387489,
        "run_id": 17
      },
      "created_at": 1795386589,
      "run_id": 17
    },
    {
      "kind": "spawned",
      "payload": {
        "pid": 1135049,
        "started_at": "bffb47f0-8c10-4c03-81ec-d65431d434c6:16|8245687"
      },
      "created_at": 1795386589,
      "run_id": 17
    },
    {
      "kind": "owner_admitted",
      "payload": {
        "db": "/home/hermes/.hermes/profiles/engineering/state.db",
        "session_id": "local-789f4871aea5397ff44d07ca626a2eb09c6e51e61b5df562d376ebc0d5c8ca73",
        "request_id": "kanban:[\"airflow-ml\",\"t_4fb5a79f\",17]",
        "pid": 817106,
        "birth": 73409.83
      },
      "created_at": 1795386590,
      "run_id": 17
    },
    {
      "kind": "worker_bound",
      "payload": {
        "pid": 1135091,
        "claim_lock": "shantanu-ubuntu:817106",
        "started_at": "bffb47f0-8c10-4c03-81ec-d65431d434c6:16|8245740"
      },
      "created_at": 1795386590,
      "run_id": 17
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795386592,
      "run_id": 17
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795386652,
      "run_id": 17
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795386717,
      "run_id": 17
    },
    {
      "kind": "linked",
      "payload": {
        "parent": "t_b64a74a1",
        "child": "t_4fb5a79f"
      },
      "created_at": 1795386762,
      "run_id": null
    },
    {
      "kind": "dependency_wait",
      "payload": {
        "reason": "Cannot dispatch yet: the README lines to polish exist only on t_b64a74a1's branches (factory/t_b64a74a1/impl-1, tip 2578bb1) — t_b64a74a1 is not merged into main (HEAD=5cf2b9d has no MLFLOW_ALLOWED_HOSTS docs), and the dispatcher only accepts base HEAD or factory/t_4fb5a79f/<window> for this ticket (cross-ticket bases rejected: 'front matter base must be HEAD or factory/<this ticket>/<window>'). This card is now parent-linked to t_b64a74a1 and will auto-resume when it completes; the impl prompt is pre-staged at /srv/software-factory/.dispatch/t_4fb5a79f--impl-1.md (base: HEAD, both nits, README-only constraints) and is ready to dispatch on resume. If you fold the two README fixes into the t_b64a74a1 merge instead, just archive this card. Note t_b64a74a1 itself is blocked on your staging acceptance (GPU VRAM guard or --force) — merging it is what unblocks both.",
        "kind": "dependency",
        "source_status": "ready"
      },
      "created_at": 1795386765,
      "run_id": 17
    },
    {
      "kind": "commented",
      "payload": {
        "author": "engineering",
        "len": 1732
      },
      "created_at": 1795386774,
      "run_id": null
    },
    {
      "kind": "worker_result",
      "payload": {
        "pid": 1135091,
        "claim_lock": "shantanu-ubuntu:817106",
        "exit_code": 0,
        "last_output": " → it's now `todo` and will **auto-resume** when t_b64a74a1 completes.\n   - Left a handoff comment with the exact re-dispatch command and acceptance checks so the resumed run acts immediately.\n\n**Operator options (both already on the card):** merge t_b64a74a1 as-is → this card re-dispatches against the updated HEAD automatically; or fold the two README fixes into that merge and archive this card. Unblocking t_b64a74a1 (free ≥8 GB VRAM or `--force`, per its block note) is what moves both forward."
      },
      "created_at": 1795386782,
      "run_id": 17
    },
    {
      "kind": "promoted",
      "payload": null,
      "created_at": 1795386987,
      "run_id": null
    },
    {
      "kind": "claimed",
      "payload": {
        "lock": "shantanu-ubuntu:817106",
        "expires": 1795387911,
        "run_id": 19
      },
      "created_at": 1795387011,
      "run_id": 19
    },
    {
      "kind": "spawned",
      "payload": {
        "pid": 1147728,
        "started_at": "bffb47f0-8c10-4c03-81ec-d65431d434c6:16|8287849"
      },
      "created_at": 1795387011,
      "run_id": 19
    },
    {
      "kind": "owner_admitted",
      "payload": {
        "db": "/home/hermes/.hermes/profiles/engineering/state.db",
        "session_id": "local-50c208ecf4b7b255ef0c169b280ff09f8fd9fde6facaab9549878212c2e6e347",
        "request_id": "kanban:[\"airflow-ml\",\"t_4fb5a79f\",19]",
        "pid": 817106,
        "birth": 73409.83
      },
      "created_at": 1795387011,
      "run_id": 19
    },
    {
      "kind": "worker_bound",
      "payload": {
        "pid": 1147783,
        "claim_lock": "shantanu-ubuntu:817106",
        "started_at": "bffb47f0-8c10-4c03-81ec-d65431d434c6:16|8287885"
      },
      "created_at": 1795387012,
      "run_id": 19
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795387013,
      "run_id": 19
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795387073,
      "run_id": 19
    },
    {
      "kind": "commented",
      "payload": {
        "author": "engineering",
        "len": 1435
      },
      "created_at": 1795387081,
      "run_id": null
    },
    {
      "kind": "blocked",
      "payload": {
        "reason": "Waiting on operator: merge factory/t_b64a74a1/impl-1 into main (t_4fb5a74a1 is approved but HEAD is still 5cf2b9d with no MLFLOW_ALLOWED_HOSTS docs, and cross-ticket bases are rejected by the dispatcher), or archive this card if the two README nits are folded into that merge. On resume: if nits are folded, verify and complete without dispatch; otherwise dispatch the pre-staged impl-1 prompt (base: HEAD).",
        "kind": "needs_input",
        "recurrences": 1,
        "source_status": "ready"
      },
      "created_at": 1795387087,
      "run_id": 19
    },
    {
      "kind": "worker_result",
      "payload": {
        "pid": 1147783,
        "claim_lock": "shantanu-ubuntu:817106",
        "exit_code": 0,
        "last_output": "hat I did**\n- Posted the full state + unblock options as a card comment (comment 19).\n- `kanban_block(kind=needs_input)`: the operator needs to either **(1)** merge `factory/t_b64a74a1/impl-1` into main — with or without folding the two README fixes in — which auto-resumes this card (I'll verify-and-close if folded, or dispatch the pre-staged `impl-1` window if not), or **(2)** archive this card if the fixes are folded into the merge.\n\nNo job or session residue was created (no dispatch was run)."
      },
      "created_at": 1795387091,
      "run_id": 19
    },
    {
      "kind": "commented",
      "payload": {
        "author": "dashboard",
        "len": 520
      },
      "created_at": 1795387279,
      "run_id": null
    },
    {
      "kind": "unblocked",
      "payload": null,
      "created_at": 1795387288,
      "run_id": null
    },
    {
      "kind": "claimed",
      "payload": {
        "lock": "shantanu-ubuntu:1154856",
        "expires": 1795388244,
        "run_id": 20
      },
      "created_at": 1795387344,
      "run_id": 20
    },
    {
      "kind": "spawned",
      "payload": {
        "pid": 1166224,
        "started_at": "bffb47f0-8c10-4c03-81ec-d65431d434c6:16|8321148"
      },
      "created_at": 1795387344,
      "run_id": 20
    },
    {
      "kind": "owner_admitted",
      "payload": {
        "db": "/home/hermes/.hermes/profiles/engineering/state.db",
        "session_id": "local-2a0f5c6c4bac86176317574646f8a5df6869e30f19046f4a830ccde62e85f934",
        "request_id": "kanban:[\"airflow-ml\",\"t_4fb5a79f\",20]",
        "pid": 1154856,
        "birth": 83021.14
      },
      "created_at": 1795387344,
      "run_id": 20
    },
    {
      "kind": "worker_bound",
      "payload": {
        "pid": 1166327,
        "claim_lock": "shantanu-ubuntu:1154856",
        "started_at": "bffb47f0-8c10-4c03-81ec-d65431d434c6:16|8321240"
      },
      "created_at": 1795387345,
      "run_id": 20
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795387347,
      "run_id": 20
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795387407,
      "run_id": 20
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795387469,
      "run_id": 20
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795387529,
      "run_id": 20
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795387590,
      "run_id": 20
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795387650,
      "run_id": 20
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795387710,
      "run_id": 20
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795387770,
      "run_id": 20
    },
    {
      "kind": "commented",
      "payload": {
        "author": "engineering",
        "len": 2110
      },
      "created_at": 1795387783,
      "run_id": null
    },
    {
      "kind": "review_requested",
      "payload": {
        "summary": "README polish (t_4fb5a79f) implemented via sandbox impl-1 window and diff-reviewed by me: both MLFLOW_ALLOWED_HOSTS nits at both doc locations (override replaces default — full-list guidance with the 403 warning; \"previous pinned list\" spelled out explicitly), plus the two folded-in t_18f19dba nits requested on the card (AIRFLOW_PROJ_DIR \"required for job containers\" reword; config/ dropped from t",
        "implementer": "engineering",
        "reviewer": null
      },
      "created_at": 1795387789,
      "run_id": 20
    },
    {
      "kind": "worker_result",
      "payload": {
        "pid": 1166327,
        "claim_lock": "shantanu-ubuntu:1154856",
        "exit_code": 0,
        "last_output": "old-in nits: AIRFLOW_PROJ_DIR row now says \"required for job containers …; compose's own airflow-service mounts fall back to `.`\", and `config/` is dropped from the job-mount list in all three places (zero `dags/, config/` residues).\n\nHandoff (branch, tip SHA, dispatch log line, verification) is posted on the card; `kanban_request_review` moved it to review (run 20). If review approves, the operator merges `factory/t_4fb5a79f/impl-1` and the ticket can be cleaned with `factory-clean t_4fb5a79f`."
      },
      "created_at": 1795387816,
      "run_id": 20
    },
    {
      "kind": "claimed",
      "payload": {
        "lock": "shantanu-ubuntu:1154856",
        "expires": 1795388726,
        "run_id": 22,
        "source_status": "review"
      },
      "created_at": 1795387826,
      "run_id": 22
    },
    {
      "kind": "spawned",
      "payload": {
        "pid": 1180408,
        "started_at": "bffb47f0-8c10-4c03-81ec-d65431d434c6:16|8369315"
      },
      "created_at": 1795387826,
      "run_id": 22
    },
    {
      "kind": "owner_admitted",
      "payload": {
        "db": "/home/hermes/.hermes/profiles/engineering/state.db",
        "session_id": "local-09d9a4313e6ce9d42b22eddabc018d3a4decbd3837ac273700c638ef2d58b4b3",
        "request_id": "kanban:[\"airflow-ml\",\"t_4fb5a79f\",22]",
        "pid": 1154856,
        "birth": 83021.14
      },
      "created_at": 1795387826,
      "run_id": 22
    },
    {
      "kind": "worker_bound",
      "payload": {
        "pid": 1180452,
        "claim_lock": "shantanu-ubuntu:1154856",
        "started_at": "bffb47f0-8c10-4c03-81ec-d65431d434c6:16|8369363"
      },
      "created_at": 1795387826,
      "run_id": 22
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795387828,
      "run_id": 22
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795387888,
      "run_id": 22
    },
    {
      "kind": "heartbeat",
      "payload": null,
      "created_at": 1795387948,
      "run_id": 22
    },
    {
      "kind": "completed",
      "payload": {
        "result_len": 0,
        "summary": "Reviewed and approved (round 1, artifact lens — cold diff read of factory/t_4fb5a79f/impl-1, commit e6ccaa0 on base 325aa68, fully independent of the handoff narrative). Both MLFLOW_ALLOWED_HOSTS nits verified present at both doc locations: \"replaces the default list rather than extending it\" with full-list guidance (`mlflow:5000,mlflow.example.com:8443`) and the 403 warning explaining the MLFLOW_"
      },
      "created_at": 1795387968,
      "run_id": 22
    },
    {
      "kind": "worker_result",
      "payload": {
        "pid": 1180452,
        "claim_lock": "shantanu-ubuntu:1154856",
        "exit_code": 0,
        "last_output": " base whose rendering was already validated in that review; bare-`*` warning intact verbatim at both spots.\n4. **Fold-in nits** (dashboard's card comment): both landed exactly as specified; diff is +5/−5 with the only non-README lines being the requested `jobtask.py` message string and compose comment line — no behaviour change, so the card's hard constraints hold.\n\nThe card is now `done`; the operator can merge `factory/t_4fb5a79f/impl-1` and run `factory-clean t_4fb5a79f` when the merge lands."
      },
      "created_at": 1795387989,
      "run_id": 22
    }
  ],
  "runs": [
    {
      "id": 17,
      "profile": "engineering",
      "step_key": null,
      "status": "blocked",
      "outcome": "blocked",
      "summary": "Cannot dispatch yet: the README lines to polish exist only on t_b64a74a1's branches (factory/t_b64a74a1/impl-1, tip 2578bb1) — t_b64a74a1 is not merged into main (HEAD=5cf2b9d has no MLFLOW_ALLOWED_HOSTS docs), and the dispatcher only accepts base HEAD or factory/t_4fb5a79f/<window> for this ticket (cross-ticket bases rejected: 'front matter base must be HEAD or factory/<this ticket>/<window>'). This card is now parent-linked to t_b64a74a1 and will auto-resume when it completes; the impl prompt is pre-staged at /srv/software-factory/.dispatch/t_4fb5a79f--impl-1.md (base: HEAD, both nits, README-only constraints) and is ready to dispatch on resume. If you fold the two README fixes into the t_b64a74a1 merge instead, just archive this card. Note t_b64a74a1 itself is blocked on your staging acceptance (GPU VRAM guard or --force) — merging it is what unblocks both.",
      "error": null,
      "metadata": null,
      "worker_pid": null,
      "started_at": 1795386589,
      "ended_at": 1795386765
    },
    {
      "id": 19,
      "profile": "engineering",
      "step_key": null,
      "status": "blocked",
      "outcome": "blocked",
      "summary": "Waiting on operator: merge factory/t_b64a74a1/impl-1 into main (t_4fb5a74a1 is approved but HEAD is still 5cf2b9d with no MLFLOW_ALLOWED_HOSTS docs, and cross-ticket bases are rejected by the dispatcher), or archive this card if the two README nits are folded into that merge. On resume: if nits are folded, verify and complete without dispatch; otherwise dispatch the pre-staged impl-1 prompt (base: HEAD).",
      "error": null,
      "metadata": null,
      "worker_pid": null,
      "started_at": 1795387011,
      "ended_at": 1795387087
    },
    {
      "id": 20,
      "profile": "engineering",
      "step_key": null,
      "status": "review",
      "outcome": "review_requested",
      "summary": "README polish (t_4fb5a79f) implemented via sandbox impl-1 window and diff-reviewed by me: both MLFLOW_ALLOWED_HOSTS nits at both doc locations (override replaces default — full-list guidance with the 403 warning; \"previous pinned list\" spelled out explicitly), plus the two folded-in t_18f19dba nits requested on the card (AIRFLOW_PROJ_DIR \"required for job containers\" reword; config/ dropped from the job-mount list in jobtask.py message, compose comment, README row). Compose fallback vs env-table default byte-identical; bare-* warning intact; docker compose config rc 0 on the branch tree; diff is prose/comment-only (+5/−5). Branch factory/t_4fb5a79f/impl-1, commit e6ccaa0, base 325aa68.",
      "error": null,
      "metadata": {
        "base": "325aa68",
        "branch": "factory/t_4fb5a79f/impl-1",
        "checks": [
          "both MLFLOW fixes at both doc locations (README L125 services row + L225 env row)",
          "env-table default byte-identical to compose ${MLFLOW_ALLOWED_HOSTS:-...} fallback",
          "bare-* warning intact at both locations",
          "fold-in nits (dashboard request): AIRFLOW_PROJ_DIR wording + config/ dropped from job-mount list in 3 places",
          "docker compose config rc 0 on branch tree (host-side, operator .env); ast.parse jobtask.py OK",
          "diff = README.md + one jobtask.py message string + one compose comment line, +5/-5"
        ],
        "commit": "e6ccaa0",
        "folded_in": "t_18f19dba nits A+B per dashboard card comment",
        "log_line": "2026-11-22 23:44:16 action=dispatch status=ok ticket=t_4fb5a79f window=impl-1 function=code_implementation harness=omp project=airflow-ml",
        "result_md": "/srv/factory-artifacts/t_4fb5a79f/impl-1/result.md",
        "tip_sha": "e6ccaa043bca74b556de03c46cbc48bb84c5207b",
        "worker_session_id": "local-2a0f5c6c4bac86176317574646f8a5df6869e30f19046f4a830ccde62e85f934"
      },
      "worker_pid": null,
      "started_at": 1795387344,
      "ended_at": 1795387789
    },
    {
      "id": 22,
      "profile": "engineering",
      "step_key": null,
      "status": "done",
      "outcome": "completed",
      "summary": "Reviewed and approved (round 1, artifact lens — cold diff read of factory/t_4fb5a79f/impl-1, commit e6ccaa0 on base 325aa68, fully independent of the handoff narrative). Both MLFLOW_ALLOWED_HOSTS nits verified present at both doc locations: \"replaces the default list rather than extending it\" with full-list guidance (`mlflow:5000,mlflow.example.com:8443`) and the 403 warning explaining the MLFLOW_TRACKING_URI drop, and \"the previous pinned list\" replaced with the explicit entries at both the services-table row and the env-table row (old phrase confirmed present in base, absent on branch). Env-table default cell is char-for-char identical to the compose `${MLFLOW_ALLOWED_HOSTS:-…}` fallback, which is unchanged from the t_b64a74a1 base already verified in its own review; the bare-`*` warning is intact verbatim at both locations and no bare `*` appears in any default/example. The two folded-in t_18f19dba nits from the dashboard card comment landed exactly as specified (AIRFLOW_PROJ_DIR \"required for job containers\" reword; `config/` dropped from the job-mount list in jobtask.py's message, the compose comment, and the README row, with zero residues) — the only non-README lines are that requested fold-in (one string literal, one comment line), a documented spec amendment, so the card's hard constraints (no MLFLOW default change, no behaviour change) hold. Ready for the operator to merge factory/t_4fb5a79f/impl-1.",
      "error": null,
      "metadata": {
        "base": "325aa68 (master HEAD = t_b64a74a1 merge)",
        "branch": "factory/t_4fb5a79f/impl-1",
        "commit": "e6ccaa0",
        "review_outcome": "approved",
        "review_round": "1 (artifact lens: cold diff read, independent of handoff narrative)",
        "reviewer_checks": [
          "cold-read git diff 325aa68..e6ccaa0: exactly 3 files, +5/-5, all prose/comments",
          "fix 1 (replaces-not-extends + full-list guidance `mlflow:5000,mlflow.example.com:8443` + 403 warning via MLFLOW_TRACKING_URI) present verbatim at both doc locations (services-table mlflow row + env-table row)",
          "fix 2: 'the previous pinned list' (verified present in base, absent on branch) replaced with explicit mlflow:5000 / localhost:5000 / 127.0.0.1:5000 + loopback wildcards at both locations",
          "env-table default cell char-for-char identical to compose ${MLFLOW_ALLOWED_HOSTS:-...} fallback; fallback unchanged from t_b64a74a1 base (its rendering already verified rc 0 in that review)",
          "bare-* warning intact verbatim at both MLFLOW locations; no bare * in any default/example value",
          "all 3 edited table rows keep balanced 3-column structure (4 pipes)",
          "fold-in nit A (dashboard comment): AIRFLOW_PROJ_DIR row = 'required for job containers ...; compose's own airflow-service mounts fall back to `.`'",
          "fold-in nit B: zero 'dags/, config/' residues in README row, compose L40 comment, jobtask.py message; jobtask diff = exactly one string literal, compose diff = exactly one comment line (no behaviour change)",
          "handoff narrative matched artifact with zero mismatches (branch/commit/base/+5-5 all confirmed)"
        ],
        "scope_caveat": "card body says 'README-only diff'; the two non-README lines (one jobtask.py message string, one compose comment) are exactly the t_18f19dba fold-in nits requested on this card by the dashboard comment and disclosed in the handoff - treated as a documented spec amendment, not scope drift; MLFLOW_ALLOWED_HOSTS default and its char-for-char match untouched per the card's hard constraint",
        "tip_sha": "e6ccaa043bca74b556de03c46cbc48bb84c5207b",
        "worker_session_id": "local-09d9a4313e6ce9d42b22eddabc018d3a4decbd3837ac273700c638ef2d58b4b3"
      },
      "worker_pid": null,
      "started_at": 1795387826,
      "ended_at": 1795387968
    }
  ]
}
```
</details>
