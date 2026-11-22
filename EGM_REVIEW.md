# EGM_REVIEW — t_29094ca2 — impl-2 (pass 2)

Branch under review: `factory/t_29094ca2/impl-2` (HEAD `498f1a4`, fix commit
`75bbcab` on top of impl-1 `ad10639`).
Scope: `jobrunner/Dockerfile`, `jobrunner/Dockerfile.gpu`, `jobrunner/constraints.txt`.
Method: static review of `git diff b5f3036 498f1a4 -- jobrunner/` and the full
files. No docker/pip was run.

## Per-item verdicts

| # | Item | Verdict | Evidence |
|---|------|---------|----------|
| B1 | fastdup METADATA path | **RESOLVED** | `Dockerfile.gpu:90` now builds the path as `Path(distribution('fastdup')._path) / 'METADATA'`. For a pip-installed wheel, `_path` is the `fastdup-2.54.dist-info` directory, so this is the real METADATA file (the old `locate_file('METADATA')` resolved to `site-packages/METADATA`). Both replacement targets are checked with `t.count(...) == 1` before the write, so a missing or duplicated pin fails the build with a named assertion instead of silently writing unchanged metadata. Replacing the prefix keeps any trailing environment marker. The one-liner is still a single double-quoted shell string with single-quoted Python literals, so the quoting is fine. |
| B2 | opencv installed before ultralytics | **RESOLVED** | Order in `Dockerfile.gpu` is now: apt `libgl1 libglib2.0-0` (63–65), then `opencv-python==4.10.0.84` (68), then `ultralytics==8.4.129` (73). When ultralytics resolves, its `opencv-python>=4.7.0,!=4.13.0.90` requirement is already met by 4.10.0.84. None of the earlier layers (deeplake, mlflow, onnx*, qdrant-client, tritonclient[all], ray[default]) pulls in `opencv-python`. The constraint `opencv-python==4.10.0.84` (item 3) is a second guard: even if the layers were reordered later, pip could not choose a 4.12+/numpy-2 build. |
| 3 | Transitive drift constraints | **RESOLVED** | `constraints.txt` is COPY'd to `/constraints.txt` in both images (CPU:26, GPU:46). Both build contexts are `jobrunner/` (compose `context: ./jobrunner`, documented GPU build command), and there is no `.dockerignore`, so the COPY works. `-c /constraints.txt` is on every resolving `pip install`: CPU 31, 38, 39, 40, 44, 45, 46; GPU 49–55, 68, 73, 91. It is left off only `--upgrade pip` (CPU 28, GPU 47) and `--no-deps fastdup==2.54` (GPU 82), as intended. The pins agree with the explicit pins in both files (numpy 1.26.4, pillow 10.4.0, scikit-learn 1.5.0, pandas 2.3.2, opencv-python 4.10.0.84). scipy (pulled in by scikit-learn/ultralytics) and pillow-heif (the final fastdup-deps layer, written `pillow_heif`; PEP 503 normalization makes it match) are now bounded. Name case differences such as `Pillow` vs `pillow` normalize too. The `opencv-python` pin in the CPU image does nothing there (nothing requires it) and does no harm. The numpy-range and wheel claims for scipy 1.16.3 and pillow-heif 0.22.0 on cp311/cp312 come from the implementation notes and were not checked here. The host build's `pip check` will confirm them. |
| 4 | `pip check` + import smoke test | **RESOLVED** | CPU: `RUN pip check` (50), then `python -c "import numpy, pandas, sklearn, scipy, deeplake, mlflow, onnx"` (53). GPU: `RUN pip check` (95), then `python -c "import numpy, cv2, fastdup, ultralytics, deeplake"` (98). Both run after the last install layer and after `COPY runner.py`, so they gate the final image. `import cv2` on the GPU image tests that the apt libGL/glib layer works with the GUI opencv build. |

## New findings

No new blocking issues found statically. Non-blocking observations for the
human reviewer:

1. **N1 (nit) — private API `_path`.** `Distribution._path` is a private
   attribute of `importlib.metadata.PathDistribution`. It works on CPython
   3.11 (GPU base) and 3.12, and the assertions make any future breakage
   fail loudly at build time rather than silently, so this is acceptable.
   A public alternative would be to pick the `METADATA` entry from
   `distribution('fastdup').files` whose parent ends in `.dist-info` and
   call `.locate()` on it.
2. **N2 (carried over from impl-1, not introduced here) — exact pins in
   the fastdup runtime-deps layer** (`Dockerfile.gpu:91`): `joblib~=1.2.0`,
   `tqdm==4.66.3`, `setuptools==78.1.1`, `sentry-sdk==2.27.0` can downgrade
   packages that earlier layers installed at newer versions. scikit-learn
   1.5.0 accepts joblib>=1.2.0. If any other installed package needs a
   newer tqdm/joblib/setuptools, the `pip check` gate will fail the build
   instead of letting it through silently. Watch this line if the host
   build's `pip check` reports a conflict.
3. **N3 (informational) — residual drift surface.** Transitive packages
   that are not constrained (matplotlib, pyarrow, polars, grpcio, ...) still
   float. The numpy/pillow/scipy pins limit how much harm they can do,
   because pip backtracks instead of upgrading the pinned stack, and
   `pip check` plus the smoke test catch whatever slips through. A full
   lock file (`pip-compile --generate-hashes`) would remove this entirely,
   but is outside this card's scope.
4. **Base-image assumptions checked:** the GPU base runs as root, so
   `apt-get` works. `libgl1`/`libglib2.0-0` exist on the Ubuntu 22.04 base
   used by the pytorch 2.7.1 runtime images. The torch 2.7.1 wheels run
   against numpy 1.26.4. The first GPU pip layer explicitly sets numpy to
   1.26.4 whatever version the base image ships. The CPU base
   (`python:3.12-slim`) has cp312 wheels for every pinned package per the
   implementation notes.

## Acceptance (not verifiable in this sandbox — for the human reviewer)

- A host `docker build` of `jobrunner/Dockerfile` and of
  `jobrunner/Dockerfile.gpu` must each finish with a clean `RUN pip check`
  and a passing import smoke test.
- The staging `voc12_full_pipeline` DAG run must succeed on the
  `ml-jobrunner-gpu:latest` image.

Verdict: APPROVE (ready for human build/staging verification)
