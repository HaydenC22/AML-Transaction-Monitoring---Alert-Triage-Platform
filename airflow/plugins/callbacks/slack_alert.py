"""DAG failure alerting. Posts to a free Slack/Discord incoming webhook if
SLACK_WEBHOOK_URL is configured; otherwise falls back to a structured JSON log
line, which is itself a legitimate (if less immediate) alerting story for an
MVP -- see the README's "what's next" section for the wire-to-Slack/PagerDuty
follow-up."""

import json
import logging
import os

import requests

logger = logging.getLogger("aml_pipeline.alerting")


def on_task_failure(context) -> None:
    task_instance = context["task_instance"]
    payload = {
        "event": "task_failure",
        "dag_id": task_instance.dag_id,
        "task_id": task_instance.task_id,
        "run_id": context["run_id"],
        "log_url": task_instance.log_url,
    }

    webhook_url = os.environ.get("SLACK_WEBHOOK_URL", "").strip()
    if webhook_url:
        try:
            requests.post(
                webhook_url,
                json={"text": f":rotating_light: AML pipeline task failed: `{payload['dag_id']}.{payload['task_id']}` "
                              f"(run {payload['run_id']})\n{payload['log_url']}"},
                timeout=5,
            )
            return
        except requests.RequestException as exc:
            logger.warning("Slack webhook post failed, falling back to log alert: %s", exc)

    logger.error(json.dumps({**payload, "sla_breached": True}))
