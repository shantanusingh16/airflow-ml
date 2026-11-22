# t_769a92a4 / egm-review-2

## Prompt as dispatched

````
---
factory:
  base: factory/t_769a92a4/impl-2
---
# Factory task t_769a92a4 — window egm-review-2 (function: egm_review)

Project: airflow-ml. You are reviewing branch `factory/t_769a92a4/impl-2`
(checked out at /work). This is review round 2 after impl-2 fixed the
findings you (round 1, on `factory/t_769a92a4/impl-1`) raised.
- Base (state under review against): `202038b` (impl-1 implementation
  commit "dags: add voc12_demo DAG + upload_voc12 job (t_769a92a4)").
- Review commit: `0068a6c` "dags: make SAMPLE a per-trigger param;
  voc12_demo review fixes (t_769a92a4)" — the tip of the implementation.
- The diff to review is `git diff 202038b..0068a6c`, EXCLUDING the
  `.factory/tickets/…` bookkeeping files (separate `factory: record …`
  commits add them — ignore). No network, no docker in this sandbox:
  code review only.

## Round-1 findings that were supposed to be fixed

1. (issue) `SAMPLE`/`VOC_DATASET_HOST_DIR` never reach the DAG (no
   env_file; not in `&airflow-common-env` → `SAMPLE` always 1000).
   Prescribed fix: (a) `Param` on the DAG with default from stack env
   `SAMPLE`, else 1000 (type integer, min 0); (b) upload task env
   `"SAMPLE": "{{ params.SAMPLE }}"`; (c)
   `DEMO_ENV["MIN_IMAGES"] = "{{ params.SAMPLE if params.SAMPLE | int > 0 else 5000 }}"`;
   (d) `SAMPLE: ${SAMPLE:-1000}` +
   `VOC_DATASET_HOST_DIR: ${VOC_DATASET_HOST_DIR:-/datasets/voc2012}`
   added to `&airflow-common-env` in docker-compose.yml (only change there);
   (e) README bullet + voc12_demo.py docstring rewritten to per-trigger
   ("Trigger w/ config" / API conf), stale "cannot be set per trigger"
   claim gone.
2. (nit) README caveat that the shared prefix `datasets/voc12/VOC2012/`
   must be empty or hold only an earlier same/smaller-sample upload
   (verify counts all JPEGs under the prefix; no pruning on shared bucket).
3. (nit) README note: default `VOC_DATASET_HOST_DIR=/datasets/voc2012` is
   the in-worker path; staging shim provides the mapping (operator
   confirms at acceptance); bare compose hosts set it to the real host
   path.
4. (nit) trailing newlines restored in `dags/voc12_demo.py` and
   `dags/jobs/upload_voc12.py`.

## Review checklist

1. Each of findings 1–4 is actually fixed as prescribed — verify the code,
   not the report: read the diff and the final file states.
2. Finding-1 mechanics on Airflow 3.x: `from airflow.sdk import Param`
   valid for this stack (check the installed airflow version / other imports
   in the repo); `params` on the DAG; `{{ params.SAMPLE }}` and the
   `params.SAMPLE | int` jinja inside `environment`/env values render at
   RUN time (DockerOperator `environment` is templated — confirm the key
   ends up in the container env as a string); `minimum=0` allows the
   SAMPLE=0 = "all 5,138" mode; a trigger with `conf: {"SAMPLE": 200}`
   overrides the default.
3. docker-compose.yml: exactly two new variables in the shared env anchor;
   YAML still valid (anchors/merge keys intact); no other service or
   variable touched; existing interpolations unchanged.
4. No regressions: `dags/voc12_demo.py` chain order/task ids unchanged
   (upload >> verify >> ingest >> embed_fastdup >> cluster_split), tags,
   schedule=None, CPU/GPU split, read-only mount on upload task only,
   MIN_IMAGES semantics (SAMPLE>0 → SAMPLE, else 5000);
   `dags/jobs/upload_voc12.py` behavior unchanged except the newline;
   `dags/jobtask.py` and all other files untouched in this round;
   nothing under .factory/ in the implementation commit.
5. README/docstring: no stale "baked at parse time / cannot pass per
   trigger" wording remains anywhere; documented trigger paths match the
   Param implementation.
6. `python3 -m py_compile` both .py files if python3 is available; else
   careful structural read.

## Required output
Your FINAL message must start with exactly one line:
  verdict: APPROVE | APPROVE-WITH-NITS | CHANGES-REQUIRED
followed by a findings table (| # | severity (nit|issue) | file | finding |)
— one row per finding, empty table if none — then a short summary. If you
require changes, each finding must state the exact expected fix.
````

## Result (final output, verdict: APPROVE)

````
verdict: APPROVE

| # | severity (nit\|issue) | file | finding |
|---|---|---|---|

No findings.

**Summary.** I reviewed `git diff 202038b..0068a6c` with `.factory/` excluded. The implementation commit changes only `README.md`, `dags/voc12_demo.py`, `dags/jobs/upload_voc12.py` and `docker-compose.yml`. It touches nothing under `.factory/` and leaves `dags/jobtask.py` alone. All four round-1 findings are fixed as prescribed. I checked the code itself, not the impl report.

- **Finding 1, SAMPLE as a per-trigger param:**
  - The DAG now has `params={"SAMPLE": Param(int(os.environ.get("SAMPLE","1000")), type="integer", minimum=0)}`.
  - `from airflow.sdk import Param` is the right import for this stack, which is `apache/airflow:3.3.1` per `Dockerfile.airflow`.
  - The upload task sets `"SAMPLE": "{{ params.SAMPLE }}"`, and `MIN_IMAGES` uses the exact Jinja that was prescribed. In Jinja the filter is applied before the comparison, so the test is `(params.SAMPLE|int) > 0`. That gives "SAMPLE if it is above 0, else 5000".
  - Both values go through `_job_env` into the `environment=` argument of `DockerOperator`/`_GpuDockerOperator`. `environment` is a templated field and nested dict values are rendered, so the values are filled in at run time and reach the container as strings.
  - `minimum=0` allows SAMPLE=0, which means "upload all". A trigger with `conf: {"SAMPLE": 200}` replaces the default.
  - `docker-compose.yml` adds exactly `SAMPLE: ${SAMPLE:-1000}` and `VOC_DATASET_HOST_DIR: ${VOC_DATASET_HOST_DIR:-/datasets/voc2012}` at the end of the `&airflow-common` environment block. The indentation matches, and no other variables or services changed.
  - The README bullet and the module docstring now describe per-trigger use ("Trigger w/ config" form, or API `conf`). No "parse time" or "cannot be set per trigger" wording is left; I grepped both files to confirm.
- **Finding 2:** the README caveat about the shared prefix is there, and it explains why verification fails when the prefix already holds more JPEGs than the current sample.
- **Finding 3:** the README note on the `VOC_DATASET_HOST_DIR` default is there: the staging shim provides the mapping and the operator confirms it at acceptance; bare compose hosts set the real host path.
- **Finding 4:** both `.py` files now end in `\n` (checked with `od -c`).

**No regressions:**
- In `dags/voc12_demo.py`, the chain is still `upload >> verify >> ingest >> embed >> cluster`, with the same task ids.
- Tags, `schedule=None`, and the CPU/GPU split are unchanged.
- The read-only dataset mount is still on the upload task only, since the GPU tasks get only `_job_mounts()`.
- In `dags/jobs/upload_voc12.py`, the only change is the trailing newline.

**Checks run:** `python3 -m py_compile` passes on both files. PyYAML isn't installed here, so I checked the YAML by reading it rather than parsing it. As agreed, there was no runtime or docker test in this sandbox.
````

## Dispatch record

```json
{
  "argv0": "/home/dev-runner/.local/bin/claude",
  "artifacts": [],
  "base_ref": "factory/t_769a92a4/impl-2",
  "base_sha": "096a0d0fa5f75d413190c6209dcb13072e9a6df0",
  "binary": "/home/dev-runner/.local/bin/claude",
  "branch": "factory/t_769a92a4/egm-review-2",
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
  "exit_file": "/srv/software-factory/.dispatch/t_769a92a4--egm-review-2.exit",
  "function": "egm_review",
  "function_class": "work",
  "harness": "claude",
  "home_seed": [
    ".claude/settings.json",
    ".claude/plugins",
    ".claude.json"
  ],
  "inputs": [],
  "install_roots": [
    "/home/dev-runner/.npm-global",
    "/home/dev-runner/.local"
  ],
  "job_dir": "/srv/factory-jobs/t_769a92a4--egm-review-2",
  "mode": "print",
  "project": "airflow-ml",
  "project_real": "/run/media/shantanu/Volume/Projects/airflow-ml",
  "prompt_file": "/srv/software-factory/.dispatch/t_769a92a4--egm-review-2.md",
  "prompt_sha256_prefix": "5f97682db4880b43",
  "resolved_via": "project_override",
  "result": {
    "sha256": "ad923e68178ae4793814960071c50fb50f5b1ce898ad840e8e4de35976ef0464",
    "stored": "/srv/factory-artifacts/t_769a92a4/egm-review-2/result.md",
    "truncated": false,
    "verdict": "APPROVE"
  },
  "routing_sha256_prefix": "a1ce7f45d24409f3",
  "secrets": [
    "ANTHROPIC_API_KEY",
    "CLAUDE_CODE_OAUTH_TOKEN"
  ],
  "spec_sha256": "538d82022d8f4094c16740a37b34f4ef6f30faa50822defd715896b7a5ffc9d1",
  "staging": null,
  "ticket": "t_769a92a4",
  "transcript": "/srv/factory-jobs/t_769a92a4--egm-review-2/transcript.log",
  "transcript_sha256": "013a01d9843a3363bf6c9392174d2390be29ba7c5f15b4b9d38895d784015c15",
  "window": "egm-review-2",
  "workdir": "/run/media/shantanu/Volume/Projects/airflow-ml",
  "workdir_rel": "."
}
```
