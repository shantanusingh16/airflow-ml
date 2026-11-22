"""Evaluation batch: run the test set through the Triton model (gRPC) and log
the "evaluate" MLflow run. Also cross-checks Triton predictions against the
numpy/sklearn train-run metrics (float32 ONNX vs float64 — small delta is
expected; > 0.05 r2 delta means the deployment is broken).

Publishes s3://<bucket>/models/<RUN_ID>/eval_metrics.json.

Reads env: RUN_ID, S3_ENDPOINT, S3_BUCKET, S3_ACCESS_KEY, S3_SECRET_KEY, S3_REGION,
           TRITON_GRPC_URL, TRITON_MODEL_NAME, MLFLOW_TRACKING_URI
"""

from __future__ import annotations

import io
import json
import os
import time

import boto3
import mlflow
import numpy as np
import pandas as pd
from botocore.config import Config
from sklearn.metrics import mean_squared_error, r2_score
from tritonclient import grpc as gc   # tritonclient>=2.68: grpc client moved from `grpcclient` to the `grpc` subpackage


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


def main() -> None:
    run_id = os.environ["RUN_ID"]
    bucket = os.environ["S3_BUCKET"]
    name = os.environ["TRITON_MODEL_NAME"]
    grpc_url = os.environ["TRITON_GRPC_URL"]
    client = s3_client()

    test = pd.read_csv(io.BytesIO(client.get_object(Bucket=bucket, Key=f"data/{run_id}/test.csv")["Body"].read()))
    info = json.loads(client.get_object(Bucket=bucket, Key=f"models/{run_id}/model_info.json")["Body"].read())
    train_metrics = json.loads(client.get_object(Bucket=bucket, Key=f"models/{run_id}/metrics.json")["Body"].read())

    feats = [c for c in test.columns if c != "target"]
    X = test[feats].values.astype(np.float32)
    y = test["target"].values

    cli = gc.InferenceServerClient(url=grpc_url)
    for _ in range(12):
        if cli.is_server_ready() and cli.is_model_ready(name):
            break
        time.sleep(10)
    else:
        raise RuntimeError(f"triton at {grpc_url} / model {name} not ready after 120s")

    in_shape = (len(X),) + tuple(int(d) for d in info["input_dims"][1:])
    inp = gc.InferInput(info["input"], in_shape, "FP32")
    inp.set_data_from_numpy(X)
    resp = cli.infer(name, inputs=[inp])
    preds = np.asarray(resp.as_numpy(info["output"]), dtype=np.float64).reshape(-1)

    r2 = float(r2_score(y, preds))
    mse = float(mean_squared_error(y, preds))
    eval_metrics = {
        "run_id": run_id,
        "inference_backend": "triton",
        "triton_model": name,
        "n_test": int(len(test)),
        "test_r2": r2,
        "test_mse": mse,
        "train_test_r2": train_metrics["test_r2"],
        "r2_delta_vs_train": abs(train_metrics["test_r2"] - r2),
    }
    if eval_metrics["r2_delta_vs_train"] > 0.05:
        raise RuntimeError(f"triton inference deviates from train metrics: {eval_metrics}")
    client.put_object(Bucket=bucket, Key=f"models/{run_id}/eval_metrics.json", Body=json.dumps(eval_metrics).encode())

    # ---- MLflow "evaluate" batch -------------------------------------------
    mlflow.set_tracking_uri(os.environ["MLFLOW_TRACKING_URI"])
    mlflow.set_experiment("ml_pipeline")
    with mlflow.start_run(run_name=f"evaluate-{run_id}"):
        mlflow.set_tag("batch", "evaluate")
        mlflow.set_tag("inference_backend", "triton")
        mlflow.set_tag("triton_model", name)
        mlflow.log_param("n_test", int(len(test)))
        mlflow.log_metric("test_r2", r2)
        mlflow.log_metric("test_mse", mse)

    print(
        f"eval via triton: test_r2={r2:.4f} test_mse={mse:.4f} "
        f"(delta vs train {eval_metrics['r2_delta_vs_train']:.6f}); mlflow run evaluate-{run_id}"
    )


if __name__ == "__main__":
    main()