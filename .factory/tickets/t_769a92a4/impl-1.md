# t_769a92a4 / impl-1

## Prompt as dispatched

````
---
factory:
  base: HEAD
---
# Factory task t_769a92a4 — window impl-1 (function: code_implementation)

Project: airflow-ml. You work in a read-only-networked git checkout; the
harness manages the branch `factory/t_769a92a4/impl-1`.

## Card (from the operator, verbatim)

Title: voc12_demo DAG: upload → verify → ingest → fastdup → cluster split (no training)

Goal: a short, demo-friendly DAG over PASCAL VOC 2012, reusing the existing voc12 jobs and stopping before training.

Dataset: read-only at /datasets/voc2012 in airflow-worker (host /run/media/shantanu/Volume/Datasets/voc2012/test, which the staging shim allows to be bind-mounted into job containers read-only). Layout: JPEGImages/ (16,135), Annotations/ (5,138 XMLs, each with at least one <object>), with no trainval.txt. Only images that have an XML count.

Changes:
1. A new job dags/jobs/upload_voc12.py (CPU, ml-jobrunner image) copies every annotated pair (or a deterministic first SAMPLE of them when SAMPLE is set) to s3://$MINIO_BUCKET/datasets/voc12/VOC2012/{JPEGImages,Annotations}/, and writes ImageSets/Main/trainval.txt listing exactly the uploaded ids. It must be idempotent (skip objects that already exist with the same size) and print counts.
2. A new dags/voc12_demo.py DAG with upload_voc12 >> verify_upload >> ingest_voc12 >> embed_fastdup >> cluster_split. It reuses the existing job scripts and DET_ENV keys, sets MIN_IMAGES to the uploaded count (default SAMPLE=1000 for a demo run of a few minutes; SAMPLE=0 means all 5,138), tags [demo, voc12], and has schedule=None.
3. README: a short "Demo pipeline (voc12_demo)" section on how to trigger it and what each step shows.

Constraints:
- Don't change voc12_full_pipeline.py or the existing job scripts, unless one of them hard-codes 5717/trainval and needs an env override (keep the defaults).
- No changes under .factory/.
- No training, evaluation or export in this DAG.

Acceptance (staging — executed by the operator, NOT in this sandbox):
- factory-env staging up airflow-ml --ref factory/t_769a92a4/impl-1, then trigger voc12_demo with SAMPLE=200.
- All 5 tasks succeed.
- MinIO shows 200 JPEGs, 200 XMLs and a trainval.txt.
- The fastdup PDF report exists at analysis/<run>/voc12_embed_report.pdf.
- The split counts are logged.

## Implementation guidance

- Research the repo first: `dags/voc12_full_pipeline.py` (task construction,
  DET_ENV keys, how MIN_IMAGES / sample envs flow to job containers),
  `dags/jobs/verify_upload.py`, `dags/jobs/ingest_voc12.py`,
  `dags/jobs/embed_fastdup.py`, `dags/jobs/cluster_split.py`, and
  `dags/jobtask.py` (cpu/gpu job task helpers, images, mounts). Match the
  existing conventions exactly: same helper functions, same env key names,
  same image names, same logging style.
- The upload job runs in a job container where the dataset is bind-mounted
  read-only at /datasets/voc2012. Derive the annotated-pair list from
  Annotations/*.xml (an image counts only if its XML exists; each XML has at
  least one <object>); deterministic order = sorted ids. When SAMPLE is set
  (int > 0) take the first SAMPLE ids in that sorted order; SAMPLE=0 (or
  unset) = all annotated pairs.
- upload_voc12 must: use $MINIO_BUCKET/$MINIO_ENDPOINT as configured by the
  DAG's env; upload JPEG + XML for each selected id; be idempotent (HEAD
  each object, skip if it exists with the same byte size); write
  datasets/voc12/VOC2012/ImageSets/Main/trainval.txt containing exactly the
  uploaded ids (one per line); and print upload/skip counts at the end.
- voc12_demo.py: five tasks chained in the order above; each task passes
  the env the corresponding existing job expects (reuse the DET_ENV keys and
  any dataset/mount env exactly as voc12_full_pipeline.py does); SAMPLE
  default 1000, SAMPLE=0 = all; MIN_IMAGES = SAMPLE value when SAMPLE > 0,
  else the full annotated count (or whatever the existing DAG uses for the
  all-annotated case — mirror it); tags = ["demo", "voc12"]; schedule=None.
- If a reused job hard-codes 5717 or a fixed trainval split, expose an env
  override in that job (default unchanged) and pass it from voc12_demo;
  record exactly what you had to touch and why.
- README: add a short "Demo pipeline (voc12_demo)" section (trigger via
  Airflow UI, SAMPLE env, what each of the 5 steps shows).
- This sandbox has NO network and NO docker: do not run pip, docker, or any
  build/run command. Your job is file edits + one commit only. You may run
  `python3 -m py_compile` on new/changed .py files if python3 is available.

## Steps (in order, exactly)

1. Research the files listed above.
2. Create dags/jobs/upload_voc12.py.
3. Create dags/voc12_demo.py.
4. Add the README section.
5. Touch existing job scripts ONLY if required by the constraint above.
6. Do not modify .factory/ or any other file.
7. Stage everything and create exactly ONE commit:
   `git commit -m "dags: add voc12_demo DAG + upload_voc12 job (t_769a92a4)"`
8. Final report: the SHA of that commit (`git rev-parse HEAD`), the branch
   tip, confirm `git status` is clean, and a short note of every file
   changed and why.
````

## Result (final output, verdict: none)

````
Working...
Done. Final report:

## Commit
- **SHA:** `202038b26bcfdc08ad1a1b8ff0750bd74cbe26ca` (parent `44b7993`)
- **Branch tip:** `factory/t_769a92a4/impl-1` → `202038b` (single commit, exact subject `dags: add voc12_demo DAG + upload_voc12 job (t_769a92a4)`)
- **`git status`:** clean — the commit contains exactly the 4 files below, nothing else touched (`.factory/`, `voc12_full_pipeline.py`, all job scripts untouched).

## Files changed
| File | Why |
|---|---|
| `dags/jobs/upload_voc12.py` (new, +121) | CPU job (ml-jobrunner): reads the read-only `/datasets/voc2012` bind mount, selects annotated pairs (`id` = XML stem, sorted, deterministic; `SAMPLE=N>0` → first N, `SAMPLE=0`/unset → all 5,138), pre-checks every selected id has its JPEG, uploads `JPEGImages/<id>.jpg` + `Annotations/<id>.xml` via boto3 against `$S3_ENDPOINT`/`$S3_BUCKET` (idempotent: HEAD each key, skip when existing size == local size), rewrites `ImageSets/Main/trainval.txt` with exactly the uploaded ids, prints upload/skip counts + `UPLOAD OK`. |
| `dags/voc12_demo.py` (new, +116) | `upload_voc12 >> verify_upload >> ingest_voc12 >> embed_fastdup >> cluster_split`, reusing the existing job scripts via `job_task`/`gpu_job_task` with the same `DET_ENV` key set (only `MIN_IMAGES` overridden: `SAMPLE` when >0, else `5000` — the full pipeline's floor), `tags=["demo","voc12"]`, `schedule=None`, `SAMPLE` default 1000 read from stack env at parse time. The upload task additionally gets a read-only bind mount `VOC_DATASET_HOST_DIR → /datasets/voc2012` (default `/datasets/voc2012`, i.e. the staging shim's dataset path). |
| `dags/jobtask.py` (+6/−2) | **Only existing file touched, DAG-side helper, not a job script:** `job_task()` gained an optional `extra_mounts` parameter (appended to the standard `dags/`+`triton-models` mounts). This was the only way to give the upload job container the dataset bind mount — no job script needed changing. `extra_mounts=None` keeps existing DAGs byte-identical in behavior; `gpu_job_task` deliberately untouched. |
| `README.md` (+49) | "Demo pipeline (`voc12_demo`)" section after the `ml_platform_pipeline` section: trigger (UI or `DAG_ID=voc12_demo make unpause/trigger/runinfo`), what each of the 5 steps shows, `SAMPLE`/`MIN_IMAGES` semantics, and the dataset-mount prerequisite (staging shim vs `VOC_DATASET_HOST_DIR` on a compose host). |

## Constraint check
- **No job scripts needed 5717/trainval env overrides** — verified: `verify_voc12_upload` reads `MIN_IMAGES`/`VOC_S3_PREFIX` from env (defaults 5000/`datasets/voc12/VOC2012`), and `ingest_voc12`/`embed_voc12`/`cluster_split_voc12` work off `DEEPLAKE_VOC12`/`DBSCAN_*` and whatever is under the S3 prefix, so a SAMPLEd upload flows through unmodified.
- No training/eval/export tasks in the DAG.

## Verified
- `python3 -m py_compile` passes on `upload_voc12.py`, `voc12_demo.py`, `jobtask.py` (Python 3.14.4).
- Selective-commit journal confirms only my 4 files were committed; worktree clean after.
- No runtime test possible here (no network/docker in sandbox, per the card); staging acceptance (SAMPLE=200 → 200 JPEGs/XMLs + `trainval.txt` in MinIO, PDF at `analysis/<run>/voc12_embed_report.pdf`, split counts logged) is operator-executed.

One operational note: `SAMPLE` is baked at DAG parse time (same convention as every other env in this stack), so `SAMPLE=200` must be in the deployment env before `factory-env staging up` — documented in the README section; it cannot be passed per-trigger.
````

## Dispatch record

```json
{
  "argv0": "/home/dev-runner/.local/bin/omp",
  "artifacts": [],
  "base_ref": "HEAD",
  "base_sha": "44b799343854f8c297d2830a1ccf7c8d06f98771",
  "binary": "/home/dev-runner/.local/bin/omp",
  "branch": "factory/t_769a92a4/impl-1",
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
  "exit_file": "/srv/software-factory/.dispatch/t_769a92a4--impl-1.exit",
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
  "job_dir": "/srv/factory-jobs/t_769a92a4--impl-1",
  "mode": "print",
  "project": "airflow-ml",
  "project_real": "/run/media/shantanu/Volume/Projects/airflow-ml",
  "prompt_file": "/srv/software-factory/.dispatch/t_769a92a4--impl-1.md",
  "prompt_sha256_prefix": "f57b200a91e3b418",
  "resolved_via": "function_default",
  "result": {
    "sha256": "8fa7f6f896c7bb00d164c502404b20408cacbe680ce73e24ba7b188baac8550f",
    "stored": "/srv/factory-artifacts/t_769a92a4/impl-1/result.md",
    "truncated": false,
    "verdict": null
  },
  "routing_sha256_prefix": "a1ce7f45d24409f3",
  "secrets": [],
  "spec_sha256": "d3f8655c9c7fd2a76eb83ada5eb4947513790493e62fe258b01495ad65d4324b",
  "staging": null,
  "ticket": "t_769a92a4",
  "transcript": "/srv/factory-jobs/t_769a92a4--impl-1/transcript.log",
  "transcript_sha256": "19ef614768f00194bd61bd0643a0b25bf693c1753eb881e75409a99400958726",
  "window": "impl-1",
  "workdir": "/run/media/shantanu/Volume/Projects/airflow-ml",
  "workdir_rel": "."
}
```
