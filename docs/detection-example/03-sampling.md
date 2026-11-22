# Stage 3 — Sampling: a deterministic, commit-pinned train/val split

> **You are at stage 3 of 7.** Outcome: the enriched `voc12` head gains a
> `split` tensor (80/20 train/val) and flat KV counts, committed as a **new
> version**. The commit id is written to the run's S3 manifest and is what
> training / evaluation / export pin — "which data was this model trained
> on" is a single string from then on.

## 3.1 Why sampling is a stage (and why it's a commit)

- **Stability.** The split is `sha256(image_id) % 100 < 20 → val`. It's a
  pure function of the image id: the same image is train-or-val on this
  machine, any other machine, any rerun. No `random.seed` roulette, no
  train/val leakage between runs.
- **Reproducibility via version.** The split is stored *in the dataset* as a
  tensor and committed. Downstream jobs load
  `deeplake.load(f"{VOC12_DATASET}@{commit_id}", read_only=True)` — the
  **commit id**, not "latest". So a model evaluated on "commit `a1b2c3d4…`"
  is exactly re-creatable even after later runs added newer commits.
- **Per-run isolation.** Because this platform rebuilds datasets per run
  (stage 2), each run gets its own dataset object + its own split commit —
  runs never interfere.

## 3.2 What `sample_voc12.py` does

`examples/detection/jobs/sample_voc12.py` (CPU image):

1. Loads the dataset **head** read-write (`deeplake.load(VOC12_DATASET,
   read_only=False, creds=…)` — head = the ingest commit from this run).
2. For every row: `split = "val" if sha256(image_id) % 100 < 20 else "train"`
   (`VAL_RATIO` env, default `0.2`).
3. `create_tensor("split", htype="text")` + `extend(splits)`.
4. Flat KV: `split_rule` (str), `val_ratio` (float), `train_count` /
   `val_count` (int), `sampled_by_run` (str).
5. `commit(message="deterministic 80/20 train/val split")` → **split commit id**.
6. Publishes `s3://ml-artifacts/data/<run_id>/voc12_split_manifest.json`:

```json
{
  "run_id": "manual__...",
  "dataset": "s3://ml-artifacts/deeplake/voc12",
  "commit_id": "a1b2c3d4e5f6...",
  "total": 5717,
  "train_count": 4573,
  "val_count": 1144,
  "val_ratio": 0.2,
  "split_rule": "sha256(image_id) % 100 < 20 -> val",
  "deeplake_ref": "s3://ml-artifacts/deeplake/voc12@a1b2c3d4e5f6..."
}
```

`deeplake_ref` is the exact version string every later stage loads.

## 3.3 Run + verify

Same mechanics as stage 2 ([02-enrichment.md §2.3](02-enrichment.md#23-how-to-run-it)):
first task after ingest in the DAG, or standalone `docker run` with the
`-v "$PWD/dags:/opt/airflow/dags:ro"` mount. Expected log tail:

```
split commit f7e8d9c0b1a2...: train=4573 val=1144 (of 5717)
manifest published: s3://ml-artifacts/data/<run_id>/voc12_split_manifest.json
SAMPLING OK: pin commit f7e8d9c0b1a2 (train=4573, val=1144)
```

Verification probe (extends the stage-2 probe):

```python
import deeplake
ds = deeplake.load("s3://ml-artifacts/deeplake/voc12", read_only=True, creds=creds)
from collections import Counter
print(Counter(ds["split"][i].numpy().item().decode() if isinstance(ds["split"][i].numpy(), bytes)
              else str(ds["split"][i].numpy()) for i in range(len(ds))))
# Counter({'train': 4573, 'val': 1144})  ← matches the KV counts in ds.info
print("kv:", {k: ds.info[k] for k in ("train_count", "val_count", "val_ratio")})
```

and check the manifest landed: MinIO console → `ml-artifacts/data/<run_id>/
/voc12_split_manifest.json`.

## 3.4 Commit ids in practice

```python
import deeplake
path = "s3://ml-artifacts/deeplake/voc12"
head  = deeplake.load(path, read_only=True, creds=creds)
print(head.commit_id)                    # newest commit (the split)
for c in head.commits:                   # full history, newest first
    print(c["commit"], c["time"], c["author"], c["message"])
# ingest commit:
ingest = head.commits[1]
d_pinned = deeplake.load(f"{path}@{ingest['commit']}", read_only=True, creds=creds)
# "split" tensor doesn't exist in that version → it's the pre-split view
```

That `path@commit` addressing is the entire versioning story: **train on
commit X, evaluate on commit X, serve what was evaluated on commit X** —
never "whatever is newest", which is how silent data drift happens.

## 3.5 Your own sampling strategies

Swap the one-liner `split_of()` for anything deterministic:

- **Stratified by class richness** (detection-specific — balance rare classes
  across the split): key the hash on `(image_id, dominant_class)`.
- **K-fold**: `fold = sha256(image_id) % K`; the training job trains on
  `fold != k` and validates on `fold == k` for each `k` — store as the same
  `fold` tensor.
- **Time-based** (video/telemetry): split by a timestamp tensor instead of a
  hash — the pattern is identical: compute per-row label, `extend()`,
  `commit(message=…)`, publish the commit id in the manifest.

**Next:** [04 — writing custom jobs and DAGs](04-custom-jobs-and-dags.md)
(you'll want this before stages 4–7, and you'll need it for any of your own
pipelines), or jump straight to
[Stage 4 — Training on the GPU](06-training-cuda.md).