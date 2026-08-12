"""AML transaction monitoring pipeline: ingest -> validate -> transform (dbt star
schema) -> validate -> detect (rules + Isolation Forest) -> transform (detection
marts) -> validate -> record run metrics.

Scheduled `@daily`, but note this MVP's ingestion step does a full idempotent
reload of the (static, synthetic) source file on every run rather than true
incremental day-by-day slicing -- a full-refresh batch pattern that's common and
appropriate at this data volume. Incremental checkpoint-based ingestion is a
documented "what's next" item once the pipeline runs against a live, growing
source. See docs/adr/0002-split-local-vs-hosted-demo.md for the broader
local-vs-hosted design this DAG only ever needs to run locally under.
"""

from datetime import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

from callbacks.slack_alert import on_task_failure

DBT_DIR = "/opt/dbt"
DBT_FLAGS = "--profiles-dir profiles --target docker"

default_args = {
    "owner": "aml-platform",
    "retries": 1,
    "on_failure_callback": on_task_failure,
}


def _check_source_file():
    from load_raw_to_warehouse import find_source_csv

    path = find_source_csv()
    print(f"Source file found: {path}")


def _ingest_raw_slice():
    from load_raw_to_warehouse import main as load_main

    load_main()


def _ge_validate_raw():
    from build_and_run_suites import validate_raw

    if not validate_raw():
        raise RuntimeError("Raw-layer Great Expectations SLA not met")


def _ge_validate_marts():
    from build_and_run_suites import validate_marts

    if not validate_marts():
        raise RuntimeError("Marts-layer Great Expectations SLA not met")


def _run_detection_engine():
    from detection.run_detection import run

    summary = run()
    if summary["rows_processed"] == 0:
        raise RuntimeError("Detection engine processed zero rows")


def _compute_pipeline_metrics():
    from detection.evaluation.evaluate_thresholds import main as evaluate_main

    result = evaluate_main()
    if not result:
        raise RuntimeError("Evaluation produced no result -- check detection.alerts")


with DAG(
    dag_id="aml_pipeline_dag",
    description="Ingest PaySim data, build the star schema, run detection, record metrics",
    default_args=default_args,
    schedule="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["aml", "data-pipeline"],
) as dag:

    check_source_file = PythonOperator(
        task_id="check_source_file",
        python_callable=_check_source_file,
    )

    ingest_raw_slice = PythonOperator(
        task_id="ingest_raw_slice",
        python_callable=_ingest_raw_slice,
    )

    ge_validate_raw = PythonOperator(
        task_id="ge_validate_raw",
        python_callable=_ge_validate_raw,
    )

    dbt_seed = BashOperator(
        task_id="dbt_seed",
        bash_command=f"cd {DBT_DIR} && dbt seed {DBT_FLAGS}",
    )

    dbt_run_staging = BashOperator(
        task_id="dbt_run_staging",
        bash_command=f"cd {DBT_DIR} && dbt run --select staging {DBT_FLAGS}",
    )

    dbt_run_intermediate = BashOperator(
        task_id="dbt_run_intermediate",
        bash_command=f"cd {DBT_DIR} && dbt run --select intermediate {DBT_FLAGS}",
    )

    dbt_run_marts_core = BashOperator(
        task_id="dbt_run_marts_core",
        bash_command=f"cd {DBT_DIR} && dbt run --select marts.core {DBT_FLAGS}",
    )

    dbt_test_core = BashOperator(
        task_id="dbt_test_core",
        bash_command=f"cd {DBT_DIR} && dbt test --select marts.core {DBT_FLAGS}",
    )

    ge_validate_marts = PythonOperator(
        task_id="ge_validate_marts",
        python_callable=_ge_validate_marts,
    )

    run_detection_engine = PythonOperator(
        task_id="run_detection_engine",
        python_callable=_run_detection_engine,
    )

    dbt_run_marts_detection = BashOperator(
        task_id="dbt_run_marts_detection",
        bash_command=f"cd {DBT_DIR} && dbt run --select marts.detection {DBT_FLAGS}",
    )

    dbt_test_marts_detection = BashOperator(
        task_id="dbt_test_marts_detection",
        bash_command=f"cd {DBT_DIR} && dbt test --select marts.detection {DBT_FLAGS}",
    )

    compute_pipeline_metrics = PythonOperator(
        task_id="compute_pipeline_metrics",
        python_callable=_compute_pipeline_metrics,
    )

    (
        check_source_file
        >> ingest_raw_slice
        >> ge_validate_raw
        >> dbt_seed
        >> dbt_run_staging
        >> dbt_run_intermediate
        >> dbt_run_marts_core
        >> dbt_test_core
        >> ge_validate_marts
        >> run_detection_engine
        >> dbt_run_marts_detection
        >> dbt_test_marts_detection
        >> compute_pipeline_metrics
    )
