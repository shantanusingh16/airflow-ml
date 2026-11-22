# t_b64a74a1 / impl-1

## Prompt as dispatched

````
---
factory:
  base: HEAD
---

# Card t_b64a74a1 — Make MLflow's allowed hosts configurable (not pinned to port 5000)

## Card body (verbatim)
factory:
  function: code_implementation
  base: HEAD

## Problem
docker-compose.yml starts MLflow with
  --allowed-hosts mlflow:5000,localhost:5000,127.0.0.1:5000,localhost,127.0.0.1
MLflow's DNS-rebinding protection then rejects any Host header with another port. In staging (UI
published on a random loopback port) the MLflow UI returns 403 Forbidden. The same would happen behind
a reverse proxy or a different published port in production.

## Change
1. Read the allowed hosts from an env var, e.g. MLFLOW_ALLOWED_HOSTS, defaulting to the current list,
   and use it in the mlflow command.
2. Check MLflow 3.15's docs for wildcard support in --allowed-hosts. If supported, the default should
   also allow any port on localhost/127.0.0.1 (e.g. `localhost:*,127.0.0.1:*`). If not, document how
   to set the exact host:port.
3. Keep the protection on: never use a bare `*`.

## Acceptance
- Staging: `sudo factory-staging up airflow-ml --ref factory/<this card>/<window>`; the MLflow URL from
  `sudo factory-staging status airflow-ml` returns HTTP 200 (no 403).
- A request with an unrelated Host header (e.g. `curl -H 'Host: evil.example' <url>`) is still rejected.
- The operator's instance on :5000 behaves as before.

## Comments
(none)

## Orchestrator decisions (final — implement exactly these, do not re-decide)
You are working in a git clone of the `airflow-ml` project at /work. Branch `factory/t_b64a74a1/impl-1` is already checked out; the base commit is the project HEAD at dispatch time. You have NO network access: do not fetch docs, do not pip install, do not run docker/podman/compose (none of it is available in this sandbox).

Decisions, made by the orchestrator from verified sources:
1. Wildcard support is CONFIRMED for the pinned MLflow v3.15.1 (base image ghcr.io/mlflow/mlflow:v3.15.1 in mlflow/Dockerfile). In v3.15.1, `mlflow/server/security_utils.py::is_allowed_host_header()` matches the full Host header string (host AND port) with `fnmatch.fnmatch` when a pattern contains `*`, else exact `==`. Therefore a pattern `localhost:*` matches `localhost:<any-port>`. MLflow's own built-in default (`get_default_allowed_hosts()`) is precisely the loopback names plus their `{name}:*` wildcards plus private-IP patterns, so adding `localhost:*` / `127.0.0.1:*` to our pinned list aligns with upstream default behavior. (Sources: https://mlflow.org/docs/latest/self-hosting/security/network and the source at tag v3.15.1.)
2. The default value = the current pinned list unchanged, plus the two loopback wildcards:
   `mlflow:5000,localhost:5000,127.0.0.1:5000,localhost,127.0.0.1,localhost:*,127.0.0.1:*`
   Keeping the old entries guarantees the operator's instance on :5000 behaves exactly as before; the wildcards fix staging (random loopback port) and reverse-proxy setups. Do NOT add any other entries (no ::1, no 0.0.0.0) and NEVER include a bare `*` (a bare `*` in the list allows ALL hosts and disables the DNS-rebinding protection).
3. Plumb it via docker compose interpolation of a host env var `MLFLOW_ALLOWED_HOSTS` (single `$`, like the existing `${MINIO_BUCKET:-ml-artifacts}` in the same command): unset/empty falls back to the default above. No Dockerfile change needed.

## Exact edits
A) docker-compose.yml — in the `mlflow` service `command: >` block, replace
     --allowed-hosts mlflow:5000,localhost:5000,127.0.0.1:5000,localhost,127.0.0.1
   with
     --allowed-hosts ${MLFLOW_ALLOWED_HOSTS:-mlflow:5000,localhost:5000,127.0.0.1:5000,localhost,127.0.0.1,localhost:*,127.0.0.1:*}
   Add a short comment line above the command (or in the mlflow section header area, matching the file's existing comment style) noting the allowed hosts are configurable via MLFLOW_ALLOWED_HOSTS and that a bare `*` must never be set.
B) README.md — in the "ML platform services" table row for `mlflow` and in the environment-variable table, document `MLFLOW_ALLOWED_HOSTS`: comma-separated Host headers the MLflow server accepts (DNS-rebinding protection); default = the value above (previous list + any port on localhost/127.0.0.1); for a reverse proxy or a differently published port, set it to the exact host[:port] the UI is reached at (e.g. `mlflow.example.com:8443`); warning: never set a bare `*` — it disables the protection.
C) Nothing else: no other services, no new files, no lock files. Keep the diff minimal.

## Verify before committing
- If `python3 -c "import yaml"` succeeds here, run `python3 -c "import yaml; yaml.safe_load(open('docker-compose.yml'))"` from /work and confirm it exits 0.
- Grep to confirm: the `--allowed-hosts` line now contains `${MLFLOW_ALLOWED_HOSTS:-` and the default ends with `localhost:*,127.0.0.1:*`; no bare `*` appears in the default list.
- `git diff` and re-read your full diff once before committing.

## Commit
`git add docker-compose.yml README.md` (only files you changed) and commit with:
  mlflow: make --allowed-hosts configurable via MLFLOW_ALLOWED_HOSTS

  Read the MLflow server's allowed Host headers from the MLFLOW_ALLOWED_HOSTS
  env var (docker compose interpolation) instead of a hardcoded list pinned to
  port 5000. The default keeps the previous entries and adds localhost:* /
  127.0.0.1:* so the UI works on any published loopback port (staging) and
  behind reverse proxies; the DNS-rebinding protection stays on (no bare *).
  Document the override in README.md.

Do not commit any .factory record files (the harness appends them after you finish), no binaries, no artifacts.
````

## Result (final output, verdict: none)

````
Working...
Done. Commit `2ec318e1b9` on `factory/t_b64a74a1/impl-1` (parent = base HEAD `5cf2b9d`), working tree clean.

**Changes (2 files, +8/−2):**
- `docker-compose.yml` — mlflow service `command: >` now uses `--allowed-hosts ${MLFLOW_ALLOWED_HOSTS:-mlflow:5000,localhost:5000,127.0.0.1:5000,localhost,127.0.0.1,localhost:*,127.0.0.1:*}` (single-`$` compose interpolation, same style as `${MINIO_BUCKET:-ml-artifacts}`), plus a comment block above the command noting the var and that a bare `*` must never be set.
- `README.md` — "ML platform services" table `mlflow` row rewritten around `MLFLOW_ALLOWED_HOSTS` (default = previous list + any loopback port; reverse proxy / other published port → exact `host[:port]`, e.g. `mlflow.example.com:8443`; never a bare `*`), and a new row in the Configuration (`.env`) table with the full default value.

**Verification:**
- Default list parsed and asserted: exactly the 7 entries, ends with `localhost:*,127.0.0.1:*`, no bare `*` (which would disable the DNS-rebinding protection).
- PyYAML is not installed in this sandbox, so the card's conditional `yaml.safe_load` check was skipped; the edits only touch comment lines and one line inside the existing folded scalar, so YAML structure is unchanged.
- `git diff` reviewed in full before committing; commit contains only the two changed files (no `.factory` files, no binaries).

**Notes:**
- The sandbox had no git identity configured; I set a repo-local `user.name`/`user.email` matching the project's existing author (Shantanu Singh) so the commit attributes correctly.
- The runtime acceptance checks (`factory-staging up airflow-ml`, HTTP 200 on the published port, 403 on `Host: evil.example`) need docker and the staging toolchain, which this sandbox doesn't have — left for the orchestrator's environment. The behavior they check follows directly from MLflow 3.15.1's `is_allowed_host_header()` fnmatch semantics on the pinned list.
````

## Dispatch record

```json
{
  "argv0": "/home/dev-runner/.local/bin/omp",
  "artifacts": [],
  "base_ref": "HEAD",
  "base_sha": "5cf2b9d141d7a6162fbbc4654850572f9e504244",
  "binary": "/home/dev-runner/.local/bin/omp",
  "branch": "factory/t_b64a74a1/impl-1",
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
  "exit_file": "/srv/software-factory/.dispatch/t_b64a74a1--impl-1.exit",
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
  "job_dir": "/srv/factory-jobs/t_b64a74a1--impl-1",
  "mode": "print",
  "project": "airflow-ml",
  "project_real": "/run/media/shantanu/Volume/Projects/airflow-ml",
  "prompt_file": "/srv/software-factory/.dispatch/t_b64a74a1--impl-1.md",
  "prompt_sha256_prefix": "093bb8086872e56e",
  "resolved_via": "function_default",
  "result": {
    "sha256": "8e3048bacbd136f261b2d53b7e3f16c64893d530740b18d46207fb59ca647ec9",
    "stored": "/srv/factory-artifacts/t_b64a74a1/impl-1/result.md",
    "truncated": false,
    "verdict": null
  },
  "routing_sha256_prefix": "a1ce7f45d24409f3",
  "secrets": [],
  "spec_sha256": "67c4a715d77b73f2362445b45fc852d8bd7fe9d41a6334c060144b7ee5a9f33c",
  "staging": null,
  "ticket": "t_b64a74a1",
  "transcript": "/srv/factory-jobs/t_b64a74a1--impl-1/transcript.log",
  "transcript_sha256": "063af173d4c25d5cecccd41f166e0535e9b67703b8a712440692a21c9a5c304e",
  "window": "impl-1",
  "workdir": "/run/media/shantanu/Volume/Projects/airflow-ml",
  "workdir_rel": "."
}
```
