# t_769a92a4 / impl-2

## Prompt as dispatched

````
---
factory:
  base: factory/t_769a92a4/impl-1
---
# Factory task t_769a92a4 — window impl-2 (function: code_implementation)

Project: airflow-ml. You continue from branch `factory/t_769a92a4/impl-1`
(the harness checks it out at /work; the implementation commit is `202038b`).
The previous window added `dags/jobs/upload_voc12.py`, `dags/voc12_demo.py`,
a small `extra_mounts` extension in `dags/jobtask.py`, and a README "Demo
pipeline (voc12_demo)" section. An independent review (egm-review) returned
**CHANGES-REQUIRED**. Fix the findings below exactly as prescribed.

## Card t_769a92a4 (context, unchanged)

Title: voc12_demo DAG: upload → verify → ingest → fastdup → cluster split (no training)

A short, demo-friendly DAG over PASCAL VOC 2012 (read-only at /datasets/voc2012
in the job container; JPEGImages/ 16,135 files, Annotations/ 5,138 XMLs each
with ≥1 <object>; only images with an XML count; no trainval.txt on disk).
New upload job (idempotent, deterministic first SAMPLE, writes
ImageSets/Main/trainval.txt with exactly the uploaded ids, prints counts),
new DAG `upload_voc12 >> verify_upload >> ingest_voc12 >> embed_fastdup >>
cluster_split` reusing existing job scripts and DET_ENV keys,
MIN_IMAGES = uploaded count, tags [demo, voc12], schedule=None, plus a
README section. No changes to voc12_full_pipeline.py or job scripts unless
an env override is required; nothing under .factory/; no training/eval/export.
Acceptance (operator, staging): trigger with SAMPLE=200 → all 5 tasks
succeed, MinIO shows 200 JPEGs + 200 XMLs + trainval.txt, fastdup PDF at
analysis/<run>/voc12_embed_report.pdf, split counts logged.

## Findings to fix (from egm-review — implement exactly this)

**FINDING 1 (issue, must fix) — `SAMPLE` and `VOC_DATASET_HOST_DIR` never
reach the DAG.** `docker-compose.yml` has no `env_file`; the Airflow
containers only get the variables in the `&airflow-common-env` block, which
lacks both names. So `os.environ.get("SAMPLE", "1000")` always returns 1000,
and a SAMPLE=200 acceptance run would upload 1,000 pairs. Fix:
(a) `from airflow.sdk import Param` (or `airflow.models.param`, whichever
the stack already imports), then on the DAG:
`params={"SAMPLE": Param(int(os.environ.get("SAMPLE", "1000")), type="integer", minimum=0)}`.
(b) In the upload task environment, set `"SAMPLE": "{{ params.SAMPLE }}"`.
(c) In `DEMO_ENV`, set
`"MIN_IMAGES": "{{ params.SAMPLE if params.SAMPLE | int > 0 else 5000 }}"`.
`DockerOperator.environment` is a templated field, so these render at run
time. (d) Add `SAMPLE: ${SAMPLE:-1000}` and
`VOC_DATASET_HOST_DIR: ${VOC_DATASET_HOST_DIR:-/datasets/voc2012}` to
`&airflow-common-env` in `docker-compose.yml`, so the parse-time default and
the bare-compose mount override actually work. (e) Rewrite the README
SAMPLE bullet and the `voc12_demo.py` docstring: SAMPLE is per-trigger via
the UI "Trigger w/ config" or API `conf: {"SAMPLE": 200}`, with the default
taken from the stack env `SAMPLE`, otherwise 1000. Drop the "cannot be set
per trigger" claim.

**FINDING 2 (nit, fix) — shared-prefix leftovers.** The prefix
`datasets/voc12/VOC2012/` is shared with the full pipeline. If it already
holds more JPEGs than the current selection (earlier bigger SAMPLE or the
5,717 full-pipeline upload), `verify_upload` fails because it counts every
JPEG under the prefix against the current trainval.txt. Pruning is NOT
acceptable on a shared bucket. Add a README caveat: the prefix should be
empty or hold only an earlier upload of the same or a smaller sample before
triggering the demo.

**FINDING 3 (nit, document) — mount source default.** The default
`VOC_DATASET_HOST_DIR` value `/datasets/voc2012` is the in-worker path; it
works only if the staging Docker shim maps it to the host path. Add one
README sentence: on the staging stack the shim provides this mapping (the
operator confirms during acceptance); on a bare compose host set
`VOC_DATASET_HOST_DIR` to the real host path.

**FINDING 4 (nit, fix) — trailing newlines.** Add a final newline to
`dags/voc12_demo.py` and `dags/jobs/upload_voc12.py`.

## Constraints (unchanged from the card)
- No changes to voc12_full_pipeline.py or the existing job scripts.
- No changes under .factory/. No training/eval/export in the DAG.
- docker-compose.yml: only the two variable additions to the shared env
  block (no other service or variable changes).

## Steps (in order, exactly)
1. Apply findings 1–4 (finding 1 in all five parts a–e).
2. Do not modify any other file. No network/docker in this sandbox: do not
   run pip, docker, or Airflow; `python3 -m py_compile` on changed .py files
   is allowed if python3 is present.
3. Stage everything and create exactly ONE commit:
   `git commit -m "dags: make SAMPLE a per-trigger param; voc12_demo review fixes (t_769a92a4)"`
4. Final report: commit SHA (`git rev-parse HEAD`), branch tip, `git status`
   clean, and a per-finding note on how it was fixed.
````

## Result (final output, verdict: none)

````
Working...
Done. All four findings fixed, one commit, clean tree.

## Final report

**Commit:** `0068a6cd388ee09f245d82ae6e19d39f3a3d5753` — branch tip of `factory/t_769a92a4/impl-2`; `git status`: nothing to commit, working tree clean. 4 files changed (README.md, docker-compose.yml, dags/voc12_demo.py, dags/jobs/upload_voc12.py); `python3 -m py_compile` passes on both changed DAG files.

**Finding 1 (SAMPLE/VOC_DATASET_HOST_DIR never reach the DAG) — fixed in all five parts:**
- **(a)** `dags/voc12_demo.py`: added `from airflow.sdk import Param` (stack is Airflow 3.3.1; no other `Param` import existed in the repo) and `params={"SAMPLE": Param(int(os.environ.get("SAMPLE", "1000")), type="integer", minimum=0)}` on the DAG.
- **(b)** upload task env is now `"SAMPLE": "{{ params.SAMPLE }}"` (renders at run time, `DockerOperator.environment` is templated).
- **(c)** `DEMO_ENV["MIN_IMAGES"] = "{{ params.SAMPLE if params.SAMPLE | int > 0 else 5000 }}"`.
- **(d)** `docker-compose.yml`: added exactly `SAMPLE: ${SAMPLE:-1000}` and `VOC_DATASET_HOST_DIR: ${VOC_DATASET_HOST_DIR:-/datasets/voc2012}` to `&airflow-common-env` (only change in that file); parse-time default and the bare-compose mount override now work.
- **(e)** Rewrote the README SAMPLE bullet and the `voc12_demo.py` docstring: SAMPLE is per-trigger via UI "Trigger w/ config" or API `conf: {"SAMPLE": 200}`, default from stack env `SAMPLE`, else 1000; the "cannot be set per trigger" claim is gone (verified no stale wording remains anywhere). The now-dead parse-time `SAMPLE` constant was removed; `VOC_DATASET_HOST_DIR` stays module-level since `mounts` is not a templated field.

**Finding 2 (shared-prefix leftovers) — fixed:** new README caveat: `verify_upload` counts every JPEG under the shared `datasets/voc12/VOC2012/` prefix, so an earlier larger `SAMPLE` or the full pipeline's 5,717-image upload makes it fail; pruning a shared bucket is not an option — keep the prefix empty or holding only an earlier same/smaller-sample upload before triggering.

**Finding 3 (mount source default) — documented:** README now states the `VOC_DATASET_HOST_DIR=/datasets/voc2012` default is the in-worker path; on staging the shim provides the mapping (operator confirms during acceptance), on a bare compose host set it to the real host path.

**Finding 4 (trailing newlines) — fixed:** both `dags/voc12_demo.py` and `dags/jobs/upload_voc12.py` now end with a final newline (verified `tail -c1` = `\n`; the `edit`/`write` tools silently drop EOF newlines in this environment, so the append went through `printf '\n' >>` — the resulting `git diff` confirms the only change in `upload_voc12.py` is the newline).

Constraints held: no changes to `voc12_full_pipeline.py` or existing job scripts, nothing under `.factory/`, no training/eval/export in the DAG.
````

## Dispatch record

```json
{
  "argv0": "/home/dev-runner/.local/bin/omp",
  "artifacts": [],
  "base_ref": "factory/t_769a92a4/impl-1",
  "base_sha": "062a9da6ff0e008a324b2436e80102c69b8ee5b2",
  "binary": "/home/dev-runner/.local/bin/omp",
  "branch": "factory/t_769a92a4/impl-2",
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
  "exit_file": "/srv/software-factory/.dispatch/t_769a92a4--impl-2.exit",
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
  "job_dir": "/srv/factory-jobs/t_769a92a4--impl-2",
  "mode": "print",
  "project": "airflow-ml",
  "project_real": "/run/media/shantanu/Volume/Projects/airflow-ml",
  "prompt_file": "/srv/software-factory/.dispatch/t_769a92a4--impl-2.md",
  "prompt_sha256_prefix": "4b762bf82e9759ee",
  "resolved_via": "function_default",
  "result": {
    "sha256": "f4ca4cc8933a9c8b789593fe32df9039ef3b89180835ebcb67436d4b4092dca1",
    "stored": "/srv/factory-artifacts/t_769a92a4/impl-2/result.md",
    "truncated": false,
    "verdict": null
  },
  "routing_sha256_prefix": "a1ce7f45d24409f3",
  "secrets": [],
  "spec_sha256": "979884d44ee9eeffbd937e4d6e21e6ceff4d93509ae20c0cff544de667f17208",
  "staging": null,
  "ticket": "t_769a92a4",
  "transcript": "/srv/factory-jobs/t_769a92a4--impl-2/transcript.log",
  "transcript_sha256": "ef90a47112494449a700eef7595c4fc5bc4af89dd8e37e71c54815f3a4575811",
  "window": "impl-2",
  "workdir": "/run/media/shantanu/Volume/Projects/airflow-ml",
  "workdir_rel": "."
}
```
