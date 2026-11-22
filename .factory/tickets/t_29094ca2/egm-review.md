# t_29094ca2 / egm-review

## Prompt as dispatched

````
---
factory:
  base: factory/t_29094ca2/impl-1
---
# EGM review — t_29094ca2 window egm-review (function: egm_review)

Project: airflow-ml. You are reviewing the branch `factory/t_29094ca2/impl-1`
(HEAD of your checkout is that branch). The change under review is commit
`ad10639e16e5eb65f435a3fd82710048036f143f`
("jobrunner: pin mutually compatible numpy/pillow/opencv stack (t_29094ca2)"),
which rewrites `jobrunner/Dockerfile` and `jobrunner/Dockerfile.gpu`.

## Card problem (operator, verbatim)

Building jobrunner/Dockerfile.gpu ended with pip reporting:
  fastdup 2.54 requires numpy<2.0,>1.23.0, but you have numpy 2.4.6
  ultralytics 8.4.129 requires opencv-python!=4.13.0.90,>=4.7.0, which is not installed
  deeplake 3.9.52 requires pillow~=10.4.0, but you have pillow 10.3.0
The pinned opencv-python-headless==4.14.0.94 pulled numpy 2 in, replacing numpy 1.26.4.
Change steps: choose a consistent set (check release notes, don't guess); satisfy
ultralytics' opencv requirement WITHOUT installing both opencv-python and the
headless build; pin pillow to what deeplake 3.9.x needs; add `RUN pip check` as the
last pip step in both Dockerfiles; keep CPU and GPU images in lock-step.

## Research evidence the fix is based on (all from PyPI metadata, verified 2026-11-22)

- fastdup 2.54 is the LAST release on PyPI (2.55/2.6 do not exist). Its exact
  requirements: pyOpenSSL>=24.0.0, joblib~=1.2.0, numpy<2.0,>1.23.0,
  pandas>=2.0.3, Pillow==10.3.0, PyYAML~=6.0, requests>=2.32.4,
  scikit-learn==1.5.0, sentry-sdk==2.27.0, setuptools==78.1.1, tqdm==4.66.3,
  psutil, pillow_heif, packaging, opencv-python-headless>=4.8.0.0.
  => the card's "numpy-2-compatible fastdup release" option does not exist;
  numpy<2 is mandatory.
- Pillow==10.3.0 (fastdup) and pillow~=10.4.0 (deeplake 3.9.52, whose pin the
  card says to follow) have an empty intersection => fastdup's pin is a
  test-time pin and must be normalized (it ran fine on pillow 10.4.x in the
  production voc12 pipeline: docs/detection-example/08-full-pipeline-fastdup-tide.md).
- ultralytics 8.4.129 requires the package name `opencv-python` (GUI);
  `opencv-python-headless` does NOT satisfy it. So the fix installs the GUI
  build + apt libgl1/libglib2.0-0 (headless `import cv2` on a server image)
  and does not install the headless build at all.
- opencv-python 4.12.0.88+ declares numpy>=2,<2.3 for py>=3.9 (numpy-2 forced);
  4.10.0.84/4.11.0.86 only declare lower bounds (numpy-1.x safe). Chosen:
  4.10.0.84.
- Base images: GPU = pytorch/pytorch:2.7.1-cuda12.8-cudnn9-runtime (Python 3.11
  conda, torch 2.7.1 + torchvision 0.22.1 preinstalled; torchvision requires
  pillow!=8.3.*,>=5.3.0 and unpinned numpy — compatible); CPU = python:3.12-slim.
- pandas pinned 2.3.2 (pre-3.0) for compatibility with fastdup 2.54 /
  scikit-learn 1.5.0; scikit-learn 1.5.0 supports both py3.11 and py3.12.

## Review checklist

1. `git show ad10639e16e5eb65f435a3fd82710048036f143f` — read the full diff.
2. Metadata-level satisfiability: walk EVERY installed package in both images
   (including preinstalled torch/torchvision on the GPU base) and confirm each
   declared requirement is satisfied by the final pinned set. Flag ANY package
   whose declared requirement the set cannot satisfy (that is exactly what
   `pip check` would report).
3. Dockerfile correctness: layer ordering (fastdup --no-deps before its
   explicit deps; opencv before fastdup so the normalized requirement is
   satisfiable; `pip check` is the LAST step in both files); shell quoting of
   the inline `python -c` metadata-normalization line; that the two
   `str.replace` targets match fastdup 2.54's METADATA exactly
   (`Requires-Dist: Pillow==10.3.0`, `Requires-Dist: opencv-python-headless>=4.8.0.0`).
4. Lock-step: the CPU Dockerfile must pin numpy/pillow/scikit-learn/pandas to
   the same values as the GPU Dockerfile; shared pins (deeplake, mlflow, onnx
   trio, qdrant-client, tritonclient, ray) must be unchanged.
5. Scope: only jobrunner/Dockerfile and jobrunner/Dockerfile.gpu changed;
   nothing under .env/.factory/dags/ touched.
6. Residual risks to call out honestly (e.g. GUI cv2 needs libGL present at
   runtime; fastdup running against pillow 10.4.x; GPU-only acceptance still
   pending host-side build + staging).

This sandbox has NO network: do not run pip/docker; reason from the metadata
evidence above and the files in the repo. Do NOT commit anything. Write your
complete findings (verdict + checklist results + any risks) to the file
`EGM_REVIEW.md` at the repository root, and also print the same report as your
final message.
````

## Dispatch record

```json
{
  "argv0": "/home/dev-runner/.local/bin/claude",
  "artifacts": [],
  "base_ref": "factory/t_29094ca2/impl-1",
  "base_sha": "b5f3036a81bddd73d32eee3ea3223afe4f341a1c",
  "binary": "/home/dev-runner/.local/bin/claude",
  "branch": "factory/t_29094ca2/egm-review",
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
  "exit_file": "/srv/software-factory/.dispatch/t_29094ca2--egm-review.exit",
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
  "job_dir": "/srv/factory-jobs/t_29094ca2--egm-review",
  "mode": "print",
  "project": "airflow-ml",
  "project_real": "/run/media/shantanu/Volume/Projects/airflow-ml",
  "prompt_file": "/srv/software-factory/.dispatch/t_29094ca2--egm-review.md",
  "prompt_sha256_prefix": "50e556fe2fa2d67d",
  "resolved_via": "project_override",
  "routing_sha256_prefix": "a1ce7f45d24409f3",
  "secrets": [
    "ANTHROPIC_API_KEY",
    "CLAUDE_CODE_OAUTH_TOKEN"
  ],
  "spec_sha256": "cdc582700998976d2f961842620b6afbd887cae27b2afadfc490dd3905103b72",
  "ticket": "t_29094ca2",
  "transcript": "/srv/factory-jobs/t_29094ca2--egm-review/transcript.log",
  "transcript_sha256": "880bacbd099c1d8fcf735066ae90f2a62c794405a1a4003d1a6bac5dd09f334f",
  "window": "egm-review",
  "workdir": "/run/media/shantanu/Volume/Projects/airflow-ml",
  "workdir_rel": "."
}
```
