"""Train a linear regression model and publish model + metrics to S3 (MinIO).

Inputs  (from generate_dataset):  data/<RUN_ID>/{train.csv,test.csv}
Outputs (published by this job):  models/<RUN_ID>/model.pkl
                                  models/<RUN_ID>/metrics.json
                                  models/<RUN_ID>/model.onnx (skl2onnx export)
Additionally: MLflow run `train-<RUN_ID>` in experiment `ml_pipeline`
(params/metrics + sklearn + ONNX models).

Reads env: RUN_ID, S3_ENDPOINT, S3_BUCKET, S3_REGION, S3_ACCESS_KEY, S3_SECRET_KEY,
           MLFLOW_TRACKING_URI
"""

from __future__ import annotations

import io
import json
import os
import pickle

import boto3
import mlflow
import numpy as np
import onnxruntime as ort
import pandas as pd
from botocore.config import Config
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
from skl2onnx import to_onnx
from skl2onnx.common.data_types import FloatTensorType


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


def download_csv(client, bucket: str, key: str) -> pd.DataFrame:
    body = client.get_object(Bucket=bucket, Key=key)["Body"].read()
    return pd.read_csv(io.BytesIO(body))


def main() -> None:
    run_id = os.environ.get("RUN_ID", "dev")
    client = s3_client()
    bucket = os.environ["S3_BUCKET"]

    train = download_csv(client, bucket, f"data/{run_id}/train.csv")
    test = download_csv(client, bucket, f"data/{run_id}/test.csv")

    feature_cols = [c for c in train.columns if c != "target"]
    X_train, y_train = train[feature_cols], train["target"]
    X_test, y_test = test[feature_cols], test["target"]

    model = LinearRegression()
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    metrics = {
        "run_id": run_id,
        "model": "LinearRegression",
        "n_train": int(len(train)),
        "n_test": int(len(test)),
        "n_features": len(feature_cols),
        "test_mse": float(mean_squared_error(y_test, y_pred)),
        "test_r2": float(r2_score(y_test, y_pred)),
        "coef": {c: float(v) for c, v in zip(feature_cols, model.coef_)},
        "intercept": float(model.intercept_),
    }

    prefix = f"models/{run_id}"
    client.put_object(Bucket=bucket, Key=f"{prefix}/metrics.json", Body=json.dumps(metrics).encode())

    buf = io.BytesIO()
    pickle.dump(model, buf)
    client.put_object(Bucket=bucket, Key=f"{prefix}/model.pkl", Body=buf.getvalue())

    # ---- ONNX export (model store + Triton input) --------------------------
    onnx_model = to_onnx(model, initial_types=[("input", FloatTensorType([None, len(feature_cols)]))], target_opset=21)
    onnx_bytes = onnx_model.SerializeToString()
    # The export must actually execute on CPU before it is published
    ort.InferenceSession(onnx_bytes, providers=["CPUExecutionProvider"]).run(
        None, {"input": X_test.values[:4].astype(np.float32)}
    )
    client.put_object(Bucket=bucket, Key=f"{prefix}/model.onnx", Body=onnx_bytes)

    # ---- MLflow "train" batch ---------------------------------------------
    mlflow.set_tracking_uri(os.environ["MLFLOW_TRACKING_URI"])
    mlflow.set_experiment("ml_pipeline")
    with mlflow.start_run(run_name=f"train-{run_id}"):
        mlflow.set_tag("batch", "train")
        mlflow.set_tag("estimator", "LinearRegression")
        mlflow.log_param("n_train", int(len(train)))
        mlflow.log_param("n_test", int(len(test)))
        mlflow.log_param("n_features", len(feature_cols))
        mlflow.log_metric("test_r2", metrics["test_r2"])
        mlflow.log_metric("test_mse", metrics["test_mse"])
        mlflow.sklearn.log_model(model, artifact_path="sklearn_model")
        mlflow.onnx.log_model(onnx_model, artifact_path="onnx_model")
        mlflow.log_dict(metrics, "metrics.json")   # 3.x fluent: log_dict(dictionary, artifact_file)
        print(f"mlflow train batch logged: {os.environ['MLFLOW_TRACKING_URI']} (run_name=train-{run_id})")

    print(
        f"model published: s3://{bucket}/{prefix}/ "
        f"(model.pkl, model.onnx, metrics.json; test_r2={metrics['test_r2']:.4f}, test_mse={metrics['test_mse']:.4f})"
    )


if __name__ == "__main__":
    main()