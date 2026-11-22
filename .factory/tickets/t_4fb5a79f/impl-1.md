# t_4fb5a79f / impl-1

## Prompt as dispatched

````
---
factory:
  base: HEAD
---

# README polish: MLFLOW_ALLOWED_HOSTS doc nits (Kanban card t_4fb5a79f)

Prerequisite: ticket t_b64a74a1 (MLFLOW_ALLOWED_HOSTS) must already be merged into main before
dispatching this — at dispatch time, HEAD's README.md must contain the `MLFLOW_ALLOWED_HOSTS` docs
(m services-table `mlflow` row ~line 125, env-var table row ~line 225). If they are missing, stop
and report it instead of inventing the content.

Prose-only polish of the `MLFLOW_ALLOWED_HOSTS` documentation in `README.md`, plus two folded-in
wording nits from the t_18f19dba review (see "Fold-in" section below). The behavior behind all of
it (compose's `--allowed-hosts ${MLFLOW_ALLOWED_HOSTS:-...}` fallback, the AIRFLOW_PROJ_DIR
passthrough, job-container mounts) is final from earlier tickets and must NOT be changed.

## Context

The MLflow server's `--allowed-hosts` (its DNS-rebinding protection, i.e. the Host headers it accepts)
is configurable via `MLFLOW_ALLOWED_HOSTS`. When the variable is unset/empty, compose falls back to the
default:

    mlflow:5000,localhost:5000,127.0.0.1:5000,localhost,127.0.0.1,localhost:*,127.0.0.1:*

i.e. a previously pinned list (`mlflow:5000`, `localhost:5000`, `127.0.0.1:5000`) plus `localhost:*` /
`127.0.0.1:*` so the UI also works on any published loopback port.

The variable is documented in two places in README.md (same variable, two rows):
- Location A: the "ML platform services" table, `mlflow` row (~line 125).
- Location B: the environment-variable table, `MLFLOW_ALLOWED_HOSTS` row (~line 225).

Apply BOTH fixes at BOTH locations A and B.

## Fix 1 — an override REPLACES the default (state it explicitly)

The current wording ("behind a reverse proxy or on a differently published port, set the exact
`host[:port]` the UI is reached at (e.g. `mlflow.example.com:8443`)") implies one can set just the
proxy host. Make explicit that setting `MLFLOW_ALLOWED_HOSTS` **replaces** the default list rather than
extending it. Warn concretely: an override containing only the reverse-proxy host (e.g.
`MLFLOW_ALLOWED_HOSTS=mlflow.example.com:8443`) drops `mlflow:5000`; every job container talks to the
server via `MLFLOW_TRACKING_URI=http://mlflow:5000`, so they would get 403 from the MLflow server.
The guidance must therefore read: set the **full** list — keep `mlflow:5000` plus the exact
`host[:port]` the UI is reached at (e.g. `mlflow:5000,mlflow.example.com:8443`). Make the full-list
form the example; the bare `mlflow.example.com:8443` form should only appear inside the warning as the
dangerous mistake.

## Fix 2 — spell out "the previous pinned list"

Both rows currently say "default = the previous pinned list plus/with ...". Replace that phrase with the
explicit entries `mlflow:5000`, `localhost:5000`, `127.0.0.1:5000` (or, alternatively, a pointer to the
full default value already shown in the env-var table — pick one, be consistent at both locations).
Preserve the meaning that the default is those pinned entries PLUS `localhost:*` / `127.0.0.1:*` (any
loopback port).

## Fold-in: t_18f19dba review nits (requested on the card; prose/comments only)

Two non-blocking nits from the review of t_18f19dba (Pass AIRFLOW_PROJ_DIR into containers) are on
main now and are folded into this polish window. Both are wording fixes; no behavior may change.

### Nit A — AIRFLOW_PROJ_DIR "required — no default" is inaccurate (README.md, `Configuration (.env)` table, `AIRFLOW_PROJ_DIR` row, ~line 208)

The row's Default column says "required — no default", but the compose file's own airflow-* service
mounts interpolate `${AIRFLOW_PROJ_DIR:-.}` (fallback to `.`), so only job containers strictly require
it (dags/jobtask.py raises if it is unset/empty). Reword the row so it says the variable is **required
for job containers** (unset/empty → job tasks fail fast) while compose's own airflow-service mounts
fall back to `.`. Keep the "meaning" column's description of what the path is used for, but fix its
mount list per Nit B.

### Nit B — wrong mount list: drop `config/` (3 locations)

`_job_mounts()` in dags/jobtask.py binds only `dags/` (read-only) and the triton model store
(`/models`) into job containers — `config/` is NOT mounted into job containers. Three places wrongly
claim it is; fix each to list only `dags/` and `triton-models/`:

1. `dags/jobtask.py` — the exception message string (~line 20, in the `if not PROJECT_DIR:` raise):
   "bind-mount dags/, config/ and triton-models/ into job containers" → "bind-mount dags/ and
   triton-models/ into job containers". Change the text only; do not alter the exception type, its
   trigger condition, or any other code.
2. `docker-compose.yml` — the comment above the `AIRFLOW_PROJ_DIR` passthrough line in the airflow
   services (~line 40): "job-task bind mounts (dags/, config/, triton-models/)" → "job-task bind
   mounts (dags/, triton-models/)". Comment text only.
3. `README.md` line ~208 (`AIRFLOW_PROJ_DIR` row, meaning column): "job containers' bind mounts
   (dags/, config/, triton-models/)" → "(dags/, triton-models/)". (Handled together with Nit A's
   reword of that row.)

## Hard constraints

- The diff may touch README.md (all fixes), and — for the fold-in nits only — the one exception
  message string in dags/jobtask.py and the one comment line in docker-compose.yml. Nothing else.
- No behavior change anywhere: no code logic, no compose values, no environment defaults.
- The default string shown in the env-var table (the "default" column of the `MLFLOW_ALLOWED_HOSTS`
  row) must remain exactly: `mlflow:5000,localhost:5000,127.0.0.1:5000,localhost,127.0.0.1,localhost:*,127.0.0.1:*`
  — it must stay character-for-character identical to the compose fallback default. Do not reword,
  reorder, or "improve" it.
- Keep the existing "never set a bare `*`" warning intact at both locations (it is already there; do
  not remove or dilute it).
- Keep the table structure valid (same number of columns, pipes balanced) in both rows you edit.

## Acceptance checks (run these in the sandbox before finishing)

1. `git diff --name-only <base>..HEAD` → at most `README.md`, `dags/jobtask.py`, `docker-compose.yml`
   (base = the branch you were given). Nothing else.
2. `git diff <base>..HEAD -- README.md` shows both MLFLOW fixes at both locations (the `mlflow`
   services-table row ~line 125 and the env-table row ~line 225) plus the folded-in nits (the
   `AIRFLOW_PROJ_DIR` row ~line 208: "required for job containers" wording, compose fallback to `.`,
   mount list without `config/`).
3. Extract the "default" cell of the `MLFLOW_ALLOWED_HOSTS` env-table row and diff it against the
   `${MLFLOW_ALLOWED_HOSTS:-...}` fallback string in docker-compose.yml → byte-identical.
   `git diff <base>..HEAD -- docker-compose.yml` shows ONLY the one comment-line change (Nit B-2);
   no compose value, env entry, or the MLFLOW fallback is touched.
   `git diff <base>..HEAD -- dags/jobtask.py` shows ONLY the exception message string change
   (Nit B-1); no code logic touched.
4. The "bare `*`" warning is still present at both MLFLOW locations.
5. `docker compose config` still renders cleanly (rc 0) and `python -c "import ast; ast.parse(open('dags/jobtask.py').read())"` passes (syntax intact).

## Out of scope

Any change to compose values, code logic, images, or the variables' default behavior — beyond the
exact comment/message rewords specified in the Fold-in section. Any other README content not covered
by the fixes above.

## Finish

Commit the change with a message like `docs: MLFLOW_ALLOWED_HOSTS override replaces default; spell out
pinned list; AIRFLOW_PROJ_DIR wording + drop config/ from job-mount list`
and end with a final summary: what changed at which lines, the acceptance-check results, and the branch
tip SHA.
````

## Result (final output, verdict: none)

````
Working...
Done. Branch `factory/t_4fb5a79f/impl-1` tip: **`e6ccaa043bca74b556de03c46cbc48bb84c5207b`** (parent = base `master` @ `325aa68`, the t_b64a74a1 merge tip — prerequisite verified present before starting).

## What changed (commit `e6ccaa04`, 3 files, +5/−5)

**README.md**
- **L125** (services table, `mlflow` row) — Fix 2: "the previous pinned list" → explicit `mlflow:5000`, `localhost:5000`, `127.0.0.1:5000` plus `localhost:*`/`127.0.0.1:*`. Fix 1: "Setting `MLFLOW_ALLOWED_HOSTS` replaces the default list rather than extending it" — guidance is now the **full list** (`mlflow:5000,mlflow.example.com:8443`); the bare proxy-host form `MLFLOW_ALLOWED_HOSTS=mlflow.example.com:8443` appears only inside the warning (drops `mlflow:5000` → job containers, which talk to the server via `MLFLOW_TRACKING_URI=http://mlflow:5000`, get 403).
- **L225** (env table, `MLFLOW_ALLOWED_HOSTS` row) — same two fixes, phrased for the table. Default cell untouched: `mlflow:5000,localhost:5000,127.0.0.1:5000,localhost,127.0.0.1,localhost:*,127.0.0.1:*`.
- **L208** (env table, `AIRFLOW_PROJ_DIR` row) — Nit A: Default cell now "required for job containers (unset/empty → job tasks fail fast — `dags/jobtask.py` raises); compose's own airflow-service mounts fall back to `.`"; Nit B: job-container mount list in the Meaning cell → `(dags/, triton-models/)` (the airflow-services clause `/opt/airflow/dags` + `config/` stays, it's accurate).

**Fold-in nits (B-1, B-2)**
- `dags/jobtask.py` L20 — exception message: "bind-mount dags/ **and** triton-models/ into job containers" (text only; `AirflowException` type and `if not PROJECT_DIR:` trigger untouched).
- `docker-compose.yml` L40 — comment: "job-task bind mounts (dags/, triton-models/)".

## Acceptance checks
1. `git diff --name-only master..HEAD` → exactly `README.md`, `dags/jobtask.py`, `docker-compose.yml`. ✓
2. README diff shows both MLFLOW fixes at L125 and L225 (full-list example, replaces-not-extends, 403 warning) plus the L208 reword. ✓
3. Default cell (L225) vs the `${MLFLOW_ALLOWED_HOSTS:-…}` fallback in compose L318 → **byte-identical** (Python string comparison). Compose diff = the one comment line only (no values/env/fallback touched); jobtask diff = the one string literal only. ✓
4. Bare-`*` warning present verbatim at both MLFLOW locations ("A bare `*` must never be set — it allows all hosts and disables the protection" / "a bare `*` disables the protection and must never be set"). ✓
5. `python3 -c "import ast; ast.parse(...)"` on `dags/jobtask.py` → OK. `docker compose config`: **not runnable here — no `docker` binary in the sandbox** (rc 127; PyPI unreachable, so no YAML lib either). Mitigated: the compose change is a single `#` comment line (diff above), which cannot affect compose rendering; the `--allowed-hosts` line and all values are diff-untouched. Table structure: all three edited rows have exactly 4 pipes (3 columns). ✓
````

## Dispatch record

```json
{
  "argv0": "/home/dev-runner/.local/bin/omp",
  "artifacts": [],
  "base_ref": "HEAD",
  "base_sha": "325aa68e9ec8337975ff759a216f0784e9ec585e",
  "binary": "/home/dev-runner/.local/bin/omp",
  "branch": "factory/t_4fb5a79f/impl-1",
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
  "exit_file": "/srv/software-factory/.dispatch/t_4fb5a79f--impl-1.exit",
  "function": "code_implementation",
  "function_class": "work",
  "harness": "omp",
  "home_seed": [
    ".omp/agent/models.yml",
    ".omp/agent/config.yml",
    ".omp/agent/mcp.json",
    ".omp/plugins",
    ".pi/agent/pi-llama-swap.json"
  ],
  "inputs": [],
  "install_roots": [
    "/home/dev-runner/.local",
    "/home/dev-runner/.omp/mcp",
    "/run/media/shantanu/Volume/Tools/pi-llama-swap"
  ],
  "job_dir": "/srv/factory-jobs/t_4fb5a79f--impl-1",
  "mode": "print",
  "project": "airflow-ml",
  "project_real": "/run/media/shantanu/Volume/Projects/airflow-ml",
  "prompt_file": "/srv/software-factory/.dispatch/t_4fb5a79f--impl-1.md",
  "prompt_sha256_prefix": "6822aacd94f688be",
  "resolved_via": "function_default",
  "result": {
    "sha256": "8e5ad755adce0b5a481e5969a2ded2f8a89fccc9a6aa496cea2a127e4c371bff",
    "stored": "/srv/factory-artifacts/t_4fb5a79f/impl-1/result.md",
    "truncated": false,
    "verdict": null
  },
  "routing_sha256_prefix": "a1ce7f45d24409f3",
  "secrets": [],
  "spec_sha256": "8da0cb464329733de2403b4306e254722cacf508f5ae75cb10d930455d19ff10",
  "staging": null,
  "ticket": "t_4fb5a79f",
  "transcript": "/srv/factory-jobs/t_4fb5a79f--impl-1/transcript.log",
  "transcript_sha256": "11af6014c5bdbf4aef19a9c9d3555149ed156cb587530081a601f7cd75d38b01",
  "window": "impl-1",
  "workdir": "/run/media/shantanu/Volume/Projects/airflow-ml",
  "workdir_rel": "."
}
```
