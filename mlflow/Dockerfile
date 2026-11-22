# MLflow 3.x server with boto3 (the base image lacks it; the S3 artifact
# store — required for --artifacts-destination s3://... against MinIO — needs it).
FROM ghcr.io/mlflow/mlflow:v3.15.1
RUN pip install --no-cache-dir boto3