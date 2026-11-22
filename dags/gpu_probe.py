"""Probe DAG: one gpu_job_task, to isolate scheduler bag-load behavior for
DAGs whose serialized operator kwargs contain docker.types.DeviceRequest
(gpu_job_task passes device_requests=[DeviceRequest(count=1,
capabilities=[["gpu"]])] to DockerOperator).

If this DAG is triggered but gets ZERO task instances (run 'succeeds'
instantly), the DeviceRequest-in-kwargs serialization is breaking the
scheduler's DAG bag load.
"""
from datetime import datetime

from airflow import DAG

from jobtask import gpu_job_task

with DAG(
    dag_id="gpu_probe",
    description="probe: single GPU task (gpu_job_task) — validates scheduler->worker->DockerOperator GPU path. Note: DAG start_date must be in the past, else manual runs phantom-succeed with 0 TIs on Airflow 3.3.1.",
    schedule=None,
    start_date=datetime(2026, 8, 26),
    catchup=False,
    tags=["probe"],
) as dag:
    gpu_job_task("probe_gpu.py", job_id="probe_gpu", timeout=600)