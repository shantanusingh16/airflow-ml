# t_29094ca2 / egm-review-2

## Prompt as dispatched

````
---
factory:
  base: factory/t_29094ca2/impl-2
---
# EGM re-review — t_29094ca2 (second pass after impl-2 fixes)

You previously reviewed `factory/t_29094ca2/impl-1` and returned **REQUEST
CHANGES** with blocking defects B1 (fastdup METADATA via
`Distribution.locate_file('METADATA')` resolves against site-packages, not the
dist-info dir, so the file does not exist and the RUN step raises
FileNotFoundError) and B2 (the `ultralytics` layer ran before
`opencv-python==4.10.0.84` was installed, letting pip resolve ultralytics'
`opencv-python>=4.7.0` requirement to a 4.12+ release that declares
numpy>=2 and upgrading numpy from 1.26.4), plus a strong recommendation to
constrain floating transitive deps (scipy, pillow-heif) so unpinned pip
layers cannot silently re-break the stack, and an import smoke test after
`pip check`.

This checkout is `factory/t_29094ca2/impl-2`, built on the impl-1 branch.
The implementation applied exactly these fixes:

1. **B1**: the METADATA rewrite now uses
   `Path(distribution('fastdup')._path) / 'METADATA'` (the dist-info path
   itself, not `locate_file`), and asserts each replacement target occurs
   exactly once (`t.count('Requires-Dist: Pillow==10.3.0') == 1`,
   `t.count('Requires-Dist: opencv-python-headless>=4.8.0.0') == 1`) so a
   mismatch fails the build loudly.
2. **B2**: the apt libGL/libglib2.0-0 layer and the
   `opencv-python==4.10.0.84` pip layer now run BEFORE the
   `ultralytics==8.4.129` layer, so ultralytics' opencv requirement is
   satisfied by the already-installed 4.10.0.84 and numpy stays 1.26.4.
3. **Transitive drift**: new shared file `jobrunner/constraints.txt`
   (numpy==1.26.4, pillow==10.4.0, scikit-learn==1.5.0, pandas==2.3.2,
   scipy==1.16.3, opencv-python==4.10.0.84, pillow-heif==0.22.0), COPY'd
   into both images and passed as `-c /constraints.txt` to every pip install
   layer in both `jobrunner/Dockerfile` (CPU) and `jobrunner/Dockerfile.gpu`
   (except `pip install --upgrade pip` and the `--no-deps fastdup` step).
   Pin rationale, verified against the packages' own METADATA on PyPI
   2026-11-22: pillow-heif 1.x all require pillow>=11.1.0 (0.22.0 is the
   last release accepting pillow 10.x, cp311/cp312 wheels exist); scipy
   1.18.x require numpy>=2.0.0 (1.16.3 allows numpy>=1.25.2,<2.6,
   cp311/cp312 wheels exist); matplotlib 3.11.2 and pyarrow 26.0.1 are
   compatible with the pins.
4. Both Dockerfiles end with `RUN pip check` followed by an import smoke
   test (`import numpy, cv2, fastdup, ultralytics, deeplake` on GPU;
   `import numpy, pandas, sklearn, scipy, deeplake, mlflow, onnx` on CPU).

## Your task

Re-review the branch (focus: jobrunner/Dockerfile, jobrunner/Dockerfile.gpu,
jobrunner/constraints.txt). For each of the four items above, state RESOLVED
or NOT-RESOLVED with evidence. Then check for any NEW blocking issues you
can identify statically (layer ordering, constraint application, base-image
assumptions). Acceptance context (unverifiable in this sandbox, noted for
the human reviewer): host `docker build` of both images must end with a
clean `pip check`, and the staging `voc12_full_pipeline` DAG run must
succeed on the GPU image.

Write your verdict to repo file `EGM_REVIEW.md` (overwrite): a header
"EGM_REVIEW — t_29094ca2 — impl-2 (pass 2)", a per-item verdict table,
any new findings, and a final line that is exactly one of:
`Verdict: APPROVE (ready for human build/staging verification)` or
`Verdict: REQUEST CHANGES (<one-line reason>)`.
Do not modify any file other than EGM_REVIEW.md. Do not run docker/pip.
````

## Dispatch record

```json
{
  "argv0": "/home/dev-runner/.local/bin/claude",
  "artifacts": [],
  "base_ref": "factory/t_29094ca2/impl-2",
  "base_sha": "498f1a4d5f69175ef31aa4a434a13aee9508a121",
  "binary": "/home/dev-runner/.local/bin/claude",
  "branch": "factory/t_29094ca2/egm-review-2",
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
  "exit_file": "/srv/software-factory/.dispatch/t_29094ca2--egm-review-2.exit",
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
  "job_dir": "/srv/factory-jobs/t_29094ca2--egm-review-2",
  "mode": "print",
  "project": "airflow-ml",
  "project_real": "/run/media/shantanu/Volume/Projects/airflow-ml",
  "prompt_file": "/srv/software-factory/.dispatch/t_29094ca2--egm-review-2.md",
  "prompt_sha256_prefix": "ce3dcde05187645b",
  "resolved_via": "project_override",
  "routing_sha256_prefix": "a1ce7f45d24409f3",
  "secrets": [
    "ANTHROPIC_API_KEY",
    "CLAUDE_CODE_OAUTH_TOKEN"
  ],
  "spec_sha256": "7c0f46362d5401998b0b910a4cc8ff4c07a9699bb350db36598ce110a93e789e",
  "ticket": "t_29094ca2",
  "transcript": "/srv/factory-jobs/t_29094ca2--egm-review-2/transcript.log",
  "transcript_sha256": "8c9a7d6a048acb1505bc8da01e597af54ef000afd72a4a107481c7e7cec620b5",
  "window": "egm-review-2",
  "workdir": "/run/media/shantanu/Volume/Projects/airflow-ml",
  "workdir_rel": "."
}
```
