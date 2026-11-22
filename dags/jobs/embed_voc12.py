"""Task 1 of 3 — FASTDUP + DINOv2 embedding & attribute extraction + PDF report.

Runs in ml-jobrunner-gpu (fastdup is installed there; its DINOv2 inference
is a CPU-optimized C++/ONNX engine — the GPU is used by the later training
tasks, not by fastdup).

For every image in the run's `voc12` DeepLake head (the stage-2 ingest
commit):

1. streams the JPEG from MinIO into the container,
2. runs **fastdup** (DINOv2-based duplicate detection): 576-dim embedding per
   image + similarity graph + connected components (= duplicate groups),
3. extracts plain image attributes (file size, mean RGB, brightness),
4. commits everything to the dataset as a new DeepLake commit:

     dinov2_embedding  (float32[576], one per image)
     is_duplicate      (int64 0/1)     dup_group (int64, -1 = unique)
     file_size         (int64 bytes)   brightness (float32)
     mean_r / mean_g / mean_b          (float32)

   plus flat KV (`num_dup_groups`, `num_duplicates`, `embedding_dim`, …)
5. renders a **PDF report** (summary, duplicate groups, embedding PCA
   scatter, most-similar pairs with thumbnails, attribute histograms) to
   `s3://<bucket>/analysis/<run_id>/voc12_embed_report.pdf`,
6. publishes `s3://<bucket>/data/<run_id>/voc12_embed_manifest.json`.

License note: fastdup is CC BY-NC-ND 4.0 (non-commercial); it also performs
a PyPI version check + Sentry telemetry at import (container has internet).
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import boto3
import cv2
import deeplake
import numpy as np
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# --- env (injected by job_task/gpu_job_task) --------------------------------
S3_ENDPOINT = os.environ["S3_ENDPOINT"]
S3_BUCKET = os.environ["S3_BUCKET"]
S3_REGION = os.environ.get("S3_REGION", "us-east-1")
S3_ACCESS = os.environ["S3_ACCESS_KEY"]
S3_SECRET = os.environ["S3_SECRET_KEY"]
RUN_ID = os.environ["RUN_ID"]

VOC12_DATASET = os.environ.get("DEEPLAKE_VOC12", "s3://ml-artifacts/deeplake/voc12")
IMGS_DIR = Path("/tmp/fdup_imgs")
WORK_DIR = Path("/tmp/fdup_work")


def s3_client() -> "boto3.client":
    return boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS,
        aws_secret_access_key=S3_SECRET,
        region_name=S3_REGION,
    )


def dl_creds() -> dict:
    return {
        "aws_access_key_id": S3_ACCESS,
        "aws_secret_access_key": S3_SECRET,
        "aws_region": S3_REGION,
        "endpoint_url": S3_ENDPOINT,
    }


def text_of(value) -> str:
    a = np.asarray(value)
    v = a.item() if a.size == 1 else a.reshape(-1)[0]
    if isinstance(v, bytes):
        v = v.decode("utf-8")
    return str(v)


def download_all(ds, s3) -> tuple[list[str], list[str]]:
    """Stream every JPEG from MinIO into IMGS_DIR. Returns (image_ids, local_paths)."""
    IMGS_DIR.mkdir(parents=True, exist_ok=True)
    ids, paths = [], []
    for i in range(len(ds["image_id"])):
        img_id = text_of(ds["image_id"][i].numpy())
        key = text_of(ds["image_uri"][i].numpy()).split("/", 3)[3]
        p = IMGS_DIR / Path(key).name
        if not p.exists():
            s3.download_file(S3_BUCKET, key, str(p))
        ids.append(img_id)
        paths.append(str(p))
    return ids, paths


def run_fastdup(ids: list[str], paths: list[str]) -> tuple[np.ndarray, dict]:
    """fastdup over all images -> (embeddings (N, D) float32 aligned to `ids`,
    per-image duplicate group map {image_id: group_int, unique=-1})."""
    import pandas as pd
    import fastdup

    print(f"fastdup {fastdup.__version__} over {len(paths)} images ...")
    t0 = time.time()
    # fastdup's C++ engine resolves annotation basenames against the process
    # CWD (job containers start in /), so the engine only finds the files if
    # we run it from inside the images directory.
    os.chdir(str(IMGS_DIR))
    fd = fastdup.create(work_dir=str(WORK_DIR), input_dir=str(IMGS_DIR))
    fd.run(input_dir=str(IMGS_DIR),
           annotations=pd.DataFrame({"filename": [os.path.basename(p) for p in paths]}),
           overwrite=True, print_summary=True)
    files, embs = fd.embeddings()          # (filenames, (N, D) float32)
    emb_by = {}
    for f, e in zip(files, embs):
        b = os.path.basename(str(f))
        emb_by[b] = e
        emb_by[b.rsplit(".", 1)[0]] = e
    missing = [i for i in ids if i not in emb_by]
    if missing:
        sys.exit(f"fastdup produced no embeddings for {len(missing)} images, e.g. {missing[:5]}")
    embs_aligned = np.stack([emb_by[i] for i in ids]).astype(np.float32)
    print(f"fastdup embeddings done in {time.time() - t0:.0f}s (dim={embs_aligned.shape[1]})")

    # duplicate groups = connected components of the similarity graph;
    # fastdup drops singletons, so images absent from the table are unique.
    group_of = {i: -1 for i in ids}
    df_cc, _ = fd.connected_components()
    n_groups, n_dups = 0, 0
    if df_cc is not None and len(df_cc):
        for _, row in df_cc.iterrows():
            base = str(row["filename"]).rsplit("/", 1)[-1].rsplit(".", 1)[0]
            if base in group_of:
                group_of[base] = int(row["component_id"])
        n_groups = int(df_cc["component_id"].nunique())
        n_dups = int(sum(1 for v in group_of.values() if v >= 0))
    return embs_aligned, {"groups": group_of, "n_groups": n_groups,
                          "n_dups": n_dups, "fd": fd, "df_cc": df_cc}


def attributes(paths: list[str]) -> dict:
    sizes, brights, mean_r, mean_g, mean_b = [], [], [], [], []
    for p in paths:
        img = cv2.imread(p, cv2.IMREAD_COLOR)
        if img is None:
            sys.exit(f"undecodable image: {p}")
        m = img.reshape(-1, 3).mean(axis=0)
        sizes.append(os.path.getsize(p))
        brights.append(float(0.299 * m[2] + 0.587 * m[1] + 0.114 * m[0]))
        mean_b.append(float(m[2])); mean_g.append(float(m[1])); mean_r.append(float(m[0]))
    return {
        "file_size": np.asarray(sizes, dtype=np.int64),
        "brightness": np.asarray(brights, dtype=np.float32),
        "mean_r": np.asarray(mean_r, dtype=np.float32),
        "mean_g": np.asarray(mean_g, dtype=np.float32),
        "mean_b": np.asarray(mean_b, dtype=np.float32),
    }


def pca2(embs: np.ndarray) -> np.ndarray:
    from sklearn.decomposition import PCA
    return PCA(n_components=2, random_state=0).fit_transform(embs)


def render_pdf(out: Path, ids, paths, embs, dup: dict, attrs: dict, n_total: int) -> None:
    """4-page PDF: summary / embedding PCA by dup group / dup table + example
    pair / attribute histograms."""
    import fastdup as _fd
    groups = dup["groups"]
    coords = pca2(embs)
    # NB: pdf.savefig(fig) must NOT use bbox_inches="tight" — on this
    # matplotlib that re-renders through the PNG path, which chokes on
    # PdfPages (AttributeError: no 'write').
    pdf = PdfPages(out)

    # --- page 1: summary ------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.axis("off")
    ax.text(0.02, 0.97, f"VOC2012 embedding & duplicate report — run {RUN_ID}",
            fontsize=14, fontweight="bold", va="top")
    lines = [
        f"Dataset          : {VOC12_DATASET}",
        f"Images analyzed  : {n_total}",
        f"Embedding model  : fastdup {_fd.__version__} (DINOv2-based, {embs.shape[1]}-dim)",
        f"Duplicate groups : {dup['n_groups']}  (images in a group: {dup['n_dups']})",
        f"Unique images    : {n_total - dup['n_dups']}",
        f"Attribute range  : brightness {attrs['brightness'].min():.0f}-{attrs['brightness'].max():.0f}, "
        f"file size {attrs['file_size'].min() // 1024}-{attrs['file_size'].max() // 1024} KB",
        f"Generated at     : {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}",
    ]
    ax.text(0.02, 0.82, "\n".join(lines), fontsize=10, va="top",
            family="monospace",
            bbox=dict(boxstyle="round", facecolor="#f2f2f2"))
    pdf.savefig(fig)
    plt.close(fig)

    # --- page 2: embedding PCA colored by duplicate group ----------------------
    fig, ax = plt.subplots(figsize=(8, 6))
    uniq = np.array([groups[i] < 0 for i in ids])
    ax.scatter(coords[uniq, 0], coords[uniq, 1], s=4, c="0.75", label="unique")
    gids = sorted({groups[i] for i in ids if groups[i] >= 0})
    cmap = plt.colormaps["tab20"]
    for gi, g in enumerate(gids):
        sel = np.asarray([k for k, i in enumerate(ids) if groups[i] == g])
        ax.scatter(coords[sel, 0], coords[sel, 1], s=6, color=cmap(gi),
                   label=f"group {g} ({len(sel)})" if gi < 15 else None)
    ax.set_title("DINOv2 embeddings (fastdup), PCA 2-D — clusters = fastdup duplicate groups")
    ax.set_xlabel("PC1")
    ax.set_ylabel("PC2")
    ax.legend(fontsize=6, loc="best")
    pdf.savefig(fig)
    plt.close(fig)

    # --- page 3: duplicate groups table + most-similar pair ---------------------
    df_cc = dup["df_cc"]
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.axis("off")
    ax.text(0.02, 0.97, f"Duplicate groups ({dup['n_groups']}) — top 20 by size",
            fontsize=12, fontweight="bold", va="top")
    if df_cc is not None and len(df_cc):
        sizes = df_cc.groupby("component_id").size().sort_values(ascending=False).head(20)
        txt = "\n".join(f"group {g}: {n} images" for g, n in sizes.items())
        ax.text(0.02, 0.90, txt, fontsize=9, family="monospace", va="top")
    pdf.savefig(fig)
    plt.close(fig)
    try:
        df_sim = dup["fd"].similarity()
        if df_sim is not None and len(df_sim):
            df_sim = df_sim.sort_values("distance", ascending=False)
            a, b = str(df_sim.iloc[0]["from"]), str(df_sim.iloc[0]["to"])
            pa, pb = IMGS_DIR / os.path.basename(a), IMGS_DIR / os.path.basename(b)
            if pa.exists() and pb.exists():
                fig2, axes2 = plt.subplots(1, 2, figsize=(8, 3.5))
                for axx, p in zip(axes2, (pa, pb)):
                    im = cv2.imread(str(p))
                    axx.imshow(im[:, :, ::-1])
                    axx.set_title(os.path.basename(p), fontsize=8)
                    axx.axis("off")
                fig2.suptitle(f"most similar pair (cosine distance {float(df_sim.iloc[0]['distance']):.3f})",
                              fontsize=9)
                pdf.savefig(fig2)
                plt.close(fig2)
    except Exception as e:  # report generation must never kill the job
        print(f"(report) similarity page skipped: {e}")

    # --- page 4: attribute histograms -------------------------------------------
    fig, axs = plt.subplots(2, 2, figsize=(8, 6))
    for axx, (name, arr) in zip(axs.ravel(),
                                (("brightness", attrs["brightness"]),
                                 ("file size (KB)", attrs["file_size"] / 1024),
                                 ("mean red", attrs["mean_r"]),
                                 ("mean green", attrs["mean_g"]))):
        axx.hist(arr, bins=40, color="#4878a8")
        axx.set_title(name, fontsize=9)
    pdf.savefig(fig)
    plt.close(fig)

    pdf.close()
    print(f"PDF report written: {out}")


def main() -> None:
    s3 = s3_client()
    creds = dl_creds()

    # head = this run's ingest commit (stage 2)
    ingest_m = json.loads(s3.get_object(
        Bucket=S3_BUCKET, Key=f"data/{RUN_ID}/voc12_ingest_manifest.json")["Body"].read())
    ds = deeplake.load(VOC12_DATASET, read_only=True, creds=creds)
    # `class_names` is per-CLASS (20 rows), not per-image; the per-image tensors
    # must all agree with each other (and with the row count we iterate over).
    per_img = [t for t in ds.tensors if t != "class_names"]
    lens = {t: len(ds[t]) for t in per_img}
    n = len(ds["image_id"])
    if n == 0:
        sys.exit(f"{VOC12_DATASET} head is empty — did ingest_voc12 run?")
    if len(set(lens.values())) > 1:
        sys.exit(f"{VOC12_DATASET} per-image tensors have inconsistent lengths {lens} — "
                 "a previous partial run left the dataset corrupt; delete it "
                 "(deeplake.delete) and re-run ingest_voc12")
    print(f"embedding {n} images from {VOC12_DATASET} (ingest commit {ingest_m['commit_id'][:12]})")

    ids, paths = download_all(ds, s3)
    missing = [p for p in paths if not os.path.exists(p)]
    if missing:
        sys.exit(f"{len(missing)} images missing on disk after download, e.g. {missing[:5]}"
                 f" — aborting before fastdup (it fails on the first missing file)")

    embs, dup = run_fastdup(ids, paths)
    attrs = attributes(paths)

    # --- commit to DeepLake ----------------------------------------------------
    ds_w = deeplake.load(VOC12_DATASET, read_only=False, creds=creds)
    names = set(ds_w.tensors)
    if "dinov2_embedding" not in names:
        ds_w.create_tensor("dinov2_embedding", htype="generic")
    for t in ("is_duplicate", "dup_group", "file_size", "brightness", "mean_r", "mean_g", "mean_b"):
        if t not in names:
            ds_w.create_tensor(t, htype="generic")

    ds_w["dinov2_embedding"].extend(list(embs))
    # NOTE: extend() gets numpy arrays, never .tolist() — deeplake 3.9's
    # intelligent_cast chokes on Python ints/floats under numpy 2 (NEP 50).
    ds_w["is_duplicate"].extend(np.asarray([1 if dup["groups"][i] >= 0 else 0 for i in ids], dtype=np.int64))
    ds_w["dup_group"].extend(np.asarray([dup["groups"][i] for i in ids], dtype=np.int64))
    ds_w["file_size"].extend(attrs["file_size"])
    ds_w["brightness"].extend(attrs["brightness"])
    ds_w["mean_r"].extend(attrs["mean_r"])
    ds_w["mean_g"].extend(attrs["mean_g"])
    ds_w["mean_b"].extend(attrs["mean_b"])

    import fastdup as _fd
    ds_w.info["embedding_model"] = f"fastdup-{_fd.__version__}-dinov2"
    ds_w.info["embedding_dim"] = int(embs.shape[1])
    ds_w.info["num_dup_groups"] = dup["n_groups"]
    ds_w.info["num_duplicates"] = dup["n_dups"]
    ds_w.info["embedded_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    ds_w.info["embedded_by_run"] = RUN_ID
    commit_id = ds_w.commit(message="fastdup DINOv2 embeddings + image attributes + duplicate groups")
    print(f"DeepLake commit {commit_id[:12]}: dinov2_embedding ({embs.shape[1]}-dim) + attributes")

    # --- PDF report + S3 publish -------------------------------------------------
    out = Path(f"/tmp/voc12_embed_report_{RUN_ID[:16]}.pdf")
    render_pdf(out, ids, paths, embs, dup, attrs, n)
    pdf_key = f"analysis/{RUN_ID}/voc12_embed_report.pdf"
    s3.upload_file(str(out), S3_BUCKET, pdf_key)
    print(f"PDF report published: s3://{S3_BUCKET}/{pdf_key}")

    manifest = {
        "run_id": RUN_ID,
        "dataset": VOC12_DATASET,
        "commit_id": commit_id,
        "deeplake_ref": f"{VOC12_DATASET}@{commit_id}",
        "image_count": n,
        "embedding_model": f"fastdup-{_fd.__version__}-dinov2",
        "embedding_dim": int(embs.shape[1]),
        "num_dup_groups": dup["n_groups"],
        "num_duplicates": dup["n_dups"],
        "tensors_added": ["dinov2_embedding", "is_duplicate", "dup_group",
                          "file_size", "brightness", "mean_r", "mean_g", "mean_b"],
        "info": dict(ds_w.info),
        "report_pdf_s3": f"s3://{S3_BUCKET}/{pdf_key}",
    }
    mkey = f"data/{RUN_ID}/voc12_embed_manifest.json"
    s3.put_object(Bucket=S3_BUCKET, Key=mkey, Body=json.dumps(manifest, indent=2).encode())
    print(f"EMBED OK: {n} images, {dup['n_groups']} dup groups; manifest {mkey}")


if __name__ == "__main__":
    t0 = time.time()
    main()
    print(f"embed_voc12 finished in {time.time() - t0:.1f}s")