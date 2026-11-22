# EGM review — t_29094ca2 / impl-1 (commit ad10639)

**Verdict: REQUEST CHANGES (do not merge).** I found two blocking defects. Each one on its own fails the GPU build. The pin choices themselves (numpy 1.26.4, pillow 10.4.0, scikit-learn 1.5.0, pandas 2.3.2, opencv-python 4.10.0.84, GUI build only, no headless) hold up against the metadata evidence. The problems are in how the Dockerfile carries those pins out.

Review method: I read the diff and the repo files, used the PyPI metadata evidence supplied in the brief, and ran one local experiment on `importlib.metadata` behaviour. There was no network, so I ran no pip and no docker.

---

## Blocking findings

### B1. The metadata-normalisation line points at a file that doesn't exist, so the build fails
`jobrunner/Dockerfile.gpu` (the `RUN python -c "..."` line after `pip install --no-deps fastdup==2.54`)

`Distribution.locate_file(path)` resolves paths against the **parent of the `.dist-info` directory** (site-packages), not against the dist-info itself. `distribution('fastdup').locate_file('METADATA')` therefore returns `.../site-packages/METADATA`, which doesn't exist, and `read_text()` raises `FileNotFoundError`. That RUN step fails.

I checked this in the sandbox:
```
>>> d.locate_file('METADATA')   -> /usr/lib/python3/dist-packages/METADATA   exists=False
>>> d._path                     -> /usr/lib/python3/dist-packages/gyp_next-0.16.2.dist-info
```
Fix: target the dist-info file itself, for example
`p = distribution('fastdup')._path / 'METADATA'`, or
`[f for f in distribution('fastdup').files if f.name == 'METADATA' and f.parent.name.endswith('.dist-info')][0].locate()`.
Also **assert that each replacement happened** (e.g. `assert t.count(old) == 1` for both targets). Without that check, a mismatched string silently does nothing and the failure only shows up later, less clearly, in `pip check`.

### B2. Layer order lets ultralytics pull in numpy 2, the same failure the card is about
`jobrunner/Dockerfile.gpu`: `ultralytics==8.4.129` is installed in its own layer **before** `opencv-python==4.10.0.84`.

At the ultralytics layer the only opencv constraint pip sees is `opencv-python>=4.7.0,!=4.13.0.90`. pip picks the newest opencv-python (4.12.0.88 or later), which declares `numpy>=2,<2.3` according to the brief's evidence. Nothing in that resolution says numpy<2. pip treats the installed numpy 1.26.4 only as a preferred candidate, not a constraint, so it **upgrades numpy to 2.2.x**. The next layer downgrades opencv to 4.10.0.84, but that version only declares a numpy lower bound, so numpy stays at 2.x. The final `pip check` then reports `fastdup 2.54 requires numpy<2.0,>1.23.0, but you have numpy 2.2.x`, which is the card's original error.

The brief's checklist asks for "opencv before fastdup". That isn't enough. opencv has to come **before or together with ultralytics**. Fix (either of):
- `RUN pip install --no-cache-dir ultralytics==8.4.129 opencv-python==4.10.0.84` (one resolution), with the apt libs layer moved above it; or
- install `opencv-python==4.10.0.84` in the layer before ultralytics.

### Strongly recommended with B2: one constraints file for every pip layer (both Dockerfiles)
B2 is one case of a wider problem. Every later `pip install` resolves its unpinned transitive dependencies to the latest release, and each of those can bump the shared pins. Candidates I could **not** rule out without network:
- **`pillow_heif`** (unpinned, fastdup-deps layer): recent pillow-heif releases declare `pillow>=11.1.0`, as far as I recall (not checked here). If that's right, this layer upgrades pillow to 11.x/12.x, and `pip check` then fails on `deeplake 3.9.52 requires pillow~=10.4.0`. This needs checking, and probably a pin to a pillow-heif version that accepts 10.4.
- scipy / matplotlib / pyarrow pulled by mlflow and ultralytics (CPU and GPU): newer scipy releases following SPEC-0 may drop numpy 1.26, and that would upgrade numpy the same way B2 does.

The research covered fastdup, opencv and deeplake, but not these floating transitive dependencies. A `constraints.txt` (`numpy==1.26.4`, `pillow==10.4.0`, `scikit-learn==1.5.0`, `pandas==2.3.2`, `opencv-python==4.10.0.84`), COPY'd first and passed as `-c` to **every** `pip install` in both files, makes pip backtrack to compatible transitive versions instead of moving the pins. It also gives one file to keep the CPU and GPU images in lock-step. (In the GPU file, fastdup's `Pillow==10.3.0` doesn't conflict with the constraint because fastdup is installed `--no-deps`.)

---

## Checklist results

**1. Diff read.** Yes. The commit changes only the two Dockerfiles (+56/−16).

**2. Metadata satisfiability (assuming B1 and B2 are fixed and no transitive drift)**

| Package (GPU unless noted) | Declared requirement | Final set | OK? |
|---|---|---|---|
| fastdup 2.54 | numpy<2.0,>1.23.0 | 1.26.4 | ✅ (❌ as written, see B2) |
| fastdup 2.54 | Pillow==10.3.0 → normalised to >=10.3.0 | 10.4.0 | ✅ only after normalisation (❌ as written, see B1) |
| fastdup 2.54 | opencv-python-headless>=4.8.0.0 → normalised to opencv-python>=4.8.0.0 | opencv-python 4.10.0.84 | ✅ only after normalisation |
| fastdup 2.54 | scikit-learn==1.5.0, pandas>=2.0.3 | 1.5.0, 2.3.2 | ✅ |
| fastdup 2.54 | joblib~=1.2.0, PyYAML~=6.0, requests>=2.32.4, setuptools==78.1.1, sentry-sdk==2.27.0, tqdm==4.66.3, pyOpenSSL>=24.0.0, psutil, pillow_heif, packaging | installed explicitly in the last pip layer | ✅ (pillow_heif → pillow risk, see above) |
| scikit-learn 1.5.0 | joblib>=1.2.0, numpy>=1.19.5, scipy>=1.6 | joblib 1.2.x after the downgrade | ✅ |
| deeplake 3.9.52 | pillow~=10.4.0 | 10.4.0 | ✅ unless a later layer bumps pillow |
| ultralytics 8.4.129 | opencv-python>=4.7.0,!=4.13.0.90 | 4.10.0.84 | ✅ |
| ultralytics 8.4.129 | pillow>=7.1.2, numpy>=1.23, tqdm>=4.64, torch/torchvision | satisfied | ✅ |
| opencv-python 4.10.0.84 | numpy lower bound only | 1.26.4 | ✅ |
| torchvision 0.22.1 (base) | torch==2.7.1, numpy, pillow!=8.3.*,>=5.3.0 | satisfied | ✅ |
| torch 2.7.1 (base) | setuptools only on py>=3.12; base is 3.11 | n/a | ✅ |
| pandas 2.3.2 | numpy>=1.23.2 (py3.11) / >=1.26.0 (py3.12, CPU) | 1.26.4 | ✅ |
| mlflow 3.15.1 / onnx 1.19.1 / onnxruntime 1.19.2 / skl2onnx 1.20.0 / tritonclient / ray / qdrant-client | lower-bounded or <3 numpy, sklearn<2, pandas<3 | satisfied | ✅ as far as I know (transitive drift not checked) |

Downgrading to tqdm 4.66.3, joblib 1.2.0 and setuptools 78.1.1 in the last layer: I know of no installed package with a higher floor. `pip check` would catch one.

**3. Dockerfile correctness**
- `--no-deps fastdup` comes before its explicit deps: ✅.
- opencv before fastdup: ✅. opencv before **ultralytics**: ❌ (B2).
- `pip check` is the last pip step in both files: ✅.
- Shell quoting of the `python -c` line: ✅. Double quotes outside, single quotes inside, and no `$`, backticks or `\`.
- Replacement targets: the strings match the brief's METADATA evidence exactly (`Requires-Dist: Pillow==10.3.0`, `Requires-Dist: opencv-python-headless>=4.8.0.0`). I couldn't check them against the real wheel offline. Add the asserts from B1.
- The METADATA path is wrong: ❌ (B1).
- Minor: after the METADATA edit, RECORD hashes no longer match. `pip check` ignores RECORD, but `pip uninstall`/reinstall of fastdup still works. Add a comment explaining this so nobody "repairs" it later.

**4. Lock-step:** ✅. The CPU file pins numpy 1.26.4, pillow 10.4.0, scikit-learn 1.5.0 and pandas 2.3.2, the same as the GPU file. The shared pins (deeplake 3.9.52, mlflow 3.15.1, onnx 1.19.1 / onnxruntime 1.19.2 / skl2onnx 1.20.0, qdrant-client 1.16.2, tritonclient[all] 2.71.0, ray[default] 2.58.0) are unchanged in both. The same transitive-drift risk applies to the CPU file, so use the shared constraints file there too.

**5. Scope:** ✅. Commit ad10639 touches only `jobrunner/Dockerfile` and `jobrunner/Dockerfile.gpu`. Nothing under `.env` or `dags/` changed. The branch's other commit (b5f3036) only adds the factory record `.factory/tickets/t_29094ca2/impl-1.md`, which is bookkeeping and not part of the change.

**6. Residual risks**
- **numpy 2 → 1.26 downgrade at runtime.** `docs/detection-example/08-full-pipeline-fastdup-tide.md` gotcha #5 shows the production pipeline (fastdup included) **ran on numpy 2**. This change moves both images back to numpy 1.26. Pickles and joblib files written by numpy-2 images (anything that references `numpy._core`, e.g. sklearn models logged to MLflow) **won't load on numpy 1.26**. NEP-50 casting semantics also differ. Existing artifacts should be re-checked.
- **Unsupported citation.** The brief says fastdup "ran fine on pillow 10.4.x" per that doc, but the doc never mentions pillow versions. It does show fastdup 2.54 ran on numpy 2, which also suggests fastdup's numpy<2 pin is test-time only. Running fastdup against pillow 10.4.0 is plausible (it's a minor bump) but unproven. Smoke-test `embed_fastdup` on the new image.
- GUI `cv2` needs `libGL.so.1` and `libgthread` at runtime. They're installed via apt in the GPU image. Any derived or slimmed image that drops them breaks `import cv2`. Add a `RUN python -c "import cv2, fastdup, ultralytics"` smoke step after `pip check`.
- The CPU image doesn't install opencv, fastdup or ultralytics, so "lock-step" covers the shared scientific pins only.
- The base image's own `pip check` cleanliness (conda-installed torch stack) is assumed, not verified.
- GPU acceptance (host-side `docker build` + staging DAG run) is still pending. Nothing here has been built.

## Required before approval
1. Fix the METADATA path and add replacement asserts (B1).
2. Install `opencv-python==4.10.0.84` before or together with ultralytics (B2).
3. Add a shared `-c constraints.txt` to every pip layer in both files, or at least pin `pillow_heif` to a version whose requirement accepts pillow 10.4.0.
4. Add an import smoke step, then run the host build + `pip check` and the staging `voc12_full_pipeline` run.
