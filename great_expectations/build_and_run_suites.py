"""Builds (idempotently) and runs the two Great Expectations suites for this project:
raw-layer validation (gates the dbt run) and marts-layer validation (gates the
detection job). Run standalone for local testing, or invoked as Airflow tasks
`ge_validate_raw` / `ge_validate_marts` in the pipeline DAG (see airflow/dags).

Exit code is non-zero if either layer's expectations fail the SLA in
EXPECTATION_SUCCESS_SLA, so it fails the calling Airflow task fast.
"""

import os
import sys

import great_expectations as gx

GE_ROOT = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = os.environ.get(
    "WAREHOUSE_DATABASE_URL",
    "postgresql://aml:aml@pg-warehouse:5432/aml_warehouse",
)
EXPECTATION_SUCCESS_SLA = 0.99  # fraction of expectations that must pass


def get_or_add_table_asset(datasource, asset_name, schema_name, table_name):
    try:
        return datasource.get_asset(asset_name)
    except LookupError:
        return datasource.add_table_asset(name=asset_name, schema_name=schema_name, table_name=table_name)


def build_raw_suite(validator):
    validator.expect_table_row_count_to_be_between(min_value=1)
    for col in ["step", "type", "amount", "nameorig", "namedest", "isfraud", "isflaggedfraud"]:
        validator.expect_column_values_to_not_be_null(col)
    validator.expect_column_values_to_be_in_set(
        "type", ["CASH_IN", "CASH_OUT", "DEBIT", "PAYMENT", "TRANSFER"]
    )
    validator.expect_column_values_to_be_in_set("isfraud", [0, 1])
    validator.expect_column_values_to_be_in_set("isflaggedfraud", [0, 1])
    validator.expect_column_values_to_be_between("amount", min_value=0)
    validator.expect_column_values_to_be_between("step", min_value=0, max_value=743)
    validator.save_expectation_suite(discard_failed_expectations=False)


def build_marts_suite(validator):
    validator.expect_table_row_count_to_be_between(min_value=1)
    validator.expect_column_values_to_be_unique("transaction_key")
    for col in ["transaction_key", "date_key", "origin_account_key", "dest_account_key", "amount"]:
        validator.expect_column_values_to_not_be_null(col)
    validator.expect_column_values_to_be_in_set(
        "transaction_type", ["CASH_IN", "CASH_OUT", "DEBIT", "PAYMENT", "TRANSFER"]
    )
    validator.expect_column_values_to_not_be_null("origin_geography_key")
    validator.expect_column_values_to_not_be_null("dest_geography_key")
    validator.save_expectation_suite(discard_failed_expectations=False)


def summarize(layer_name, result) -> bool:
    stats = result["statistics"]
    evaluated = max(stats["evaluated_expectations"], 1)
    success_rate = stats["successful_expectations"] / evaluated
    print(
        f"[{layer_name}] {stats['successful_expectations']}/{stats['evaluated_expectations']} "
        f"expectations passed ({success_rate:.1%})"
    )
    if success_rate < EXPECTATION_SUCCESS_SLA:
        print(f"[{layer_name}] FAILED: below {EXPECTATION_SUCCESS_SLA:.0%} SLA")
        return False
    print(f"[{layer_name}] PASSED")
    return True


def validate_layer(context, datasource, asset_name, schema_name, table_name, suite_name, build_fn) -> bool:
    # Suite definitions live in this script, not as accumulated state, so each run
    # rebuilds the suite from scratch rather than erroring on "already exists".
    if suite_name in context.list_expectation_suite_names():
        context.delete_expectation_suite(suite_name)

    asset = get_or_add_table_asset(datasource, asset_name, schema_name, table_name)
    validator = context.get_validator(
        batch_request=asset.build_batch_request(),
        create_expectation_suite_with_name=suite_name,
    )
    build_fn(validator)
    result = validator.validate()
    return summarize(schema_name, result)


def main() -> int:
    context = gx.get_context(mode="file", project_root_dir=GE_ROOT)
    datasource = context.sources.add_or_update_postgres(
        name="aml_warehouse", connection_string=DATABASE_URL
    )

    raw_ok = validate_layer(
        context, datasource,
        "raw_paysim_transactions", "raw", "paysim_transactions",
        "raw_transactions_suite", build_raw_suite,
    )
    marts_ok = validate_layer(
        context, datasource,
        "marts_fact_transactions", "raw_marts_core", "fact_transactions",
        "marts_fact_transactions_suite", build_marts_suite,
    )

    return 0 if (raw_ok and marts_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
