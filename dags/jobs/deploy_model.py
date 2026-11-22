"""Stage the exported ONNX model into the Triton repository and load it.

The job container and the triton service bind-mount the same host directory
(<PROJECT_DIR>/triton-models) as /models, so writing model.onnx + config.pbtxt
locally makes the model visible to Triton after a repository re-index
(explicit model control). The Triton config is generated from the ONNX graph
so input/output names always match. Layout follows the Triton 26.x convention:
config.pbtxt at the model root (/models/<name>/config.pbtxt) and the model
file under the version dir (/models/<name>/1/model.onnx); with max_batch_size
> 0 Triton prepends the batch dim implicitly, so config dims carry only the
non-batch dimensions of the ONNX graph.

Publishes s3://<bucket>/models/<RUN_ID>/{config.pbtxt,model_info.json}.

Reads env: RUN_ID, S3_ENDPOINT, S3_BUCKET, S3_ACCESS_KEY, S3_SECRET_KEY, S3_REGION,
           TRITON_HTTP_URL, TRITON_GRPC_URL, TRITON_MODEL_NAME
"""

from __future__ import annotations

import json
import os
import time

import boto3
import onnx
import requests
from tritonclient import grpc as gc
from botocore.config import Config
from onnx import TensorProto

TYPE_MAP = {
    TensorProto.FLOAT: "TYPE_FP32",
    TensorProto.DOUBLE: "TYPE_FP64",
    TensorProto.INT32: "TYPE_INT32",
    TensorProto.INT64: "TYPE_INT64",
    TensorProto.STRING: "TYPE_STRING",
}

# Batch cap for the deployed ONNX model: the graph has a dynamic leading
# batch dim (to_onnx initial type [None, n_features]); 1024 comfortably
# covers the smoke batch (2 rows) and the full test-set batch sent by
# evaluate. Must stay in sync with config_text() and the verify loop in
# main().
MAX_BATCH_SIZE = 1024

def s3_client():
    return boto3.client(
        "s3",
        endpoint_url=os.environ["S3_ENDPOINT"],
        region_name=os.environ.get("S3_REGION", "us-east-1"),
        aws_access_key_id=os.environ.get("S3_ACCESS_KEY", "minioadmin"),
        aws_secret_access_key=os.environ.get("S3_SECRET_KEY", "minioadmin"),
        config=Config(s3={"addressing_style": "path"}),
        verify=False,
    )


def dims_of(value_info) -> list:
    out = []
    for d in value_info.type.tensor_type.shape.dim:
        out.append(int(d.dim_value) if d.HasField("dim_value") and d.dim_value > 0 else 0)
    return out


def config_dims(value_info) -> list:
    """Non-batch dims for the Triton 26.x config: the leading dynamic (batch)
    dim of the ONNX graph is dropped because Triton prepends an implicit
    batch dim when max_batch_size > 0."""
    dims = dims_of(value_info)
    if dims and dims[0] == 0:
        dims = dims[1:]
    return dims


def config_text(m: onnx.ModelProto, name: str) -> str:
    blocks = []
    for vi, section in ((m.graph.input[0], "input"), (m.graph.output[0], "output")):
        dt = TYPE_MAP.get(vi.type.tensor_type.elem_type)
        if dt is None:
            raise RuntimeError(f"unsupported ONNX elem_type {vi.type.tensor_type.elem_type} for Triton")
        blocks.append(
            f"{section} [\n  {{\n    name: \"{vi.name}\"\n    data_type: {dt}\n"
            f"    dims: [ {', '.join(str(d) for d in config_dims(vi))} ]\n  }}\n]"
        )
    return f'name: "{name}"\nbackend: "onnxruntime"\nmax_batch_size: {MAX_BATCH_SIZE}\n' + "\n".join(blocks) + "\n"


def main() -> None:
    run_id = os.environ["RUN_ID"]
    bucket = os.environ["S3_BUCKET"]
    name = os.environ["TRITON_MODEL_NAME"]
    http = os.environ["TRITON_HTTP_URL"]
    client = s3_client()

    onnx_bytes = client.get_object(Bucket=bucket, Key=f"models/{run_id}/model.onnx")["Body"].read()
    m = onnx.load_from_string(onnx_bytes)
    cfg = config_text(m, name)

    # Stage into the shared model repository (atomic per-file replace).
    # 26.x layout: config at the model root, model file under the version dir.
    model_root = f"/models/{name}"
    version_dir = f"{model_root}/1"
    os.makedirs(version_dir, exist_ok=True)
    for target, payload in (
        (f"{version_dir}/model.onnx", onnx_bytes),
        (f"{model_root}/config.pbtxt", cfg.encode("utf-8")),
    ):
        tmp = target + ".staging"
        with open(tmp, "wb") as f:
            f.write(payload)
        os.replace(tmp, target)

    # Explicit model control over gRPC: Triton 26.07's HTTP
    # /v2/models/{name}/load endpoint returns 404 even for models that are
    # present in the repository (26.07 regression); the gRPC ModelLoad /
    # ModelIsReady RPCs behave correctly. HTTP is still used for the smoke
    # inference below.
    # The model repo is a bind mount shared with the triton container; on
    # FUSE-backed volumes new files can take a moment to become visible there,
    # so retry the repository index until the model shows up.
    grpc_cli = gc.InferenceServerClient(url=os.environ["TRITON_GRPC_URL"])
    deadline = time.time() + 60
    seen = False
    while time.time() < deadline:
        idx = grpc_cli.get_model_repository_index()  # also triggers a repo re-scan
        seen = name in [mm.name for mm in idx.models]
        if seen:
            break
        time.sleep(2)
    if not seen:
        raise RuntimeError(f"model {name} not visible in Triton repository after 60s of re-indexing")
    try:
        grpc_cli.unload_model(name)
    except Exception:
        pass  # not loaded yet (first deploy) — fine
    grpc_cli.load_model(name)
    # Verify Triton actually used our config.pbtxt rather than its
    # non-strict auto-completed fallback: if the staged config file is not
    # yet visible through the shared bind mount (FUSE visibility lag),
    # Triton silently generates a default config from the ONNX file
    # (e.g. max_batch_size 4). Re-index and reload until the loaded
    # config matches what we staged.
    deadline = time.time() + 90
    while True:
        st = requests.get(f"{http}/v2/models/{name}/config", timeout=10)
        st.raise_for_status()
        if st.json().get("max_batch_size") == MAX_BATCH_SIZE:
            break
        if time.time() > deadline:
            raise RuntimeError(
                f"model {name} loaded with unexpected config "
                f"(max_batch_size={st.json().get('max_batch_size')}, expected {MAX_BATCH_SIZE}); "
                "staged config.pbtxt may not be visible in the triton container"
            )
        try:
            grpc_cli.unload_model(name)
        except Exception:
            pass
        time.sleep(2)
        grpc_cli.get_model_repository_index()
        grpc_cli.load_model(name)
    deadline = time.time() + 120
    ready = False
    while time.time() < deadline:
        if grpc_cli.is_model_ready(name):
            ready = True
            break
        time.sleep(5)
    if not ready:
        raise RuntimeError(f"model {name} not ready in Triton after 120s")

    # Smoke inference over HTTP: two dummy rows through the deployed model
    in_name = m.graph.input[0].name
    zero = [0.0] * 8
    r = requests.post(
        f"{http}/v2/models/{name}/infer",
        timeout=30,
        json={"inputs": [{"name": in_name, "shape": [2, 8], "datatype": "FP32", "data": zero + zero}]},
    )
    r.raise_for_status()
    sample_out = r.json()["outputs"][0]["data"][:2]
    print(f"triton model ready: {name} (sample outputs={sample_out})")

    info = {
        "model_name": name,
        "input": in_name,
        "output": m.graph.output[0].name,
        "input_dims": dims_of(m.graph.input[0]),
        "output_dims": dims_of(m.graph.output[0]),
    }
    client.put_object(Bucket=bucket, Key=f"models/{run_id}/config.pbtxt", Body=cfg.encode("utf-8"))
    client.put_object(Bucket=bucket, Key=f"models/{run_id}/model_info.json", Body=json.dumps(info).encode())
    print(f"model deployed: triton://{name} (run {run_id}); info at s3://{bucket}/models/{run_id}/model_info.json")


if __name__ == "__main__":
    main()