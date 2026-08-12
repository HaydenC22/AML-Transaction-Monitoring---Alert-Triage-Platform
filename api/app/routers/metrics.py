from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.schemas import OverviewMetrics, RuleVolume, ThresholdPoint, ThresholdRecommendation, TimelinePoint

router = APIRouter(prefix="/metrics", tags=["metrics"])
CURRENT_THRESHOLD = 0.60  # mirrors detection/evaluation/evaluate_thresholds.CHOSEN_THRESHOLD


@router.get("/overview", response_model=OverviewMetrics)
def overview(db: Session = Depends(get_db)):
    alert_volume = db.execute(
        text(
            """
            select day_offset, count(*) as alert_count
            from raw_marts_detection.fct_alerts
            group by day_offset order by day_offset
            """
        )
    ).mappings().all()

    fp_rate_trend = db.execute(
        text(
            """
            select
                date(d.dispositioned_at) as day,
                round(
                    100.0 * count(*) filter (where d.outcome = 'false_positive') / count(*), 2
                ) as fp_rate_pct,
                count(*) as dispositions
            from app.alert_dispositions d
            group by 1 order by 1
            """
        )
    ).mappings().all()

    severity_breakdown = db.execute(
        text(
            """
            select severity, count(*) as alert_count,
                   count(*) filter (where is_fraud_label) as true_positive_count
            from raw_marts_detection.fct_alerts
            group by severity
            """
        )
    ).mappings().all()

    analyst_throughput = db.execute(
        text(
            """
            select date(dispositioned_at) as day, count(*) as dispositions
            from app.alert_dispositions
            group by 1 order by 1
            """
        )
    ).mappings().all()

    latest_run = db.execute(
        text(
            """
            select run_id, run_at, rows_processed, alerts_generated,
                   precision_at_threshold::float, recall_at_threshold::float,
                   fp_rate_at_threshold::float, runtime_seconds::float, ge_status
            from pipeline_state.pipeline_runs
            order by run_id desc limit 1
            """
        )
    ).mappings().first()

    return OverviewMetrics(
        alert_volume_by_day=[dict(r) for r in alert_volume],
        fp_rate_trend=[dict(r) for r in fp_rate_trend],
        severity_breakdown=[dict(r) for r in severity_breakdown],
        analyst_throughput_by_day=[dict(r) for r in analyst_throughput],
        latest_pipeline_run=dict(latest_run) if latest_run else None,
    )


@router.get("/cases/{alert_id}/timeline", response_model=list[TimelinePoint])
def case_timeline(alert_id: int, db: Session = Depends(get_db)):
    alert = db.execute(
        text("select origin_account_nk from raw_marts_detection.fct_alerts where alert_id = :alert_id"),
        {"alert_id": alert_id},
    ).mappings().first()
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")

    rows = db.execute(
        text(
            """
            select d.simulated_day_offset as day_offset, count(*) as transaction_count,
                   sum(f.amount)::float as total_amount
            from raw_marts_core.fact_transactions f
            join raw_marts_core.dim_account a on a.account_key = f.origin_account_key
            join raw_marts_core.dim_date d on d.date_key = f.date_key
            where a.account_nk = :account_nk
            group by d.simulated_day_offset
            order by d.simulated_day_offset
            """
        ),
        {"account_nk": alert["origin_account_nk"]},
    ).mappings().all()
    return [TimelinePoint(**dict(r)) for r in rows]


@router.get("/threshold-curve", response_model=list[ThresholdPoint])
def threshold_curve(db: Session = Depends(get_db)):
    """Recomputed live from detection.alerts on every request -- always reflects
    the current alert population rather than a stale generated file."""
    rows = db.execute(
        text("select composite_score::float as composite_score, is_fraud_label from detection.alerts")
    ).mappings().all()
    total_fraud = db.execute(
        text("select count(*) as c from raw_marts_core.fact_transactions where is_fraud_label")
    ).scalar_one()
    total_txns = db.execute(text("select count(*) as c from raw_marts_core.fact_transactions")).scalar_one()

    if not rows or not total_txns:
        return []

    points = []
    threshold = 0.05
    while threshold <= 1.001:
        t = round(threshold, 2)
        flagged = [r for r in rows if r["composite_score"] >= t]
        tp = sum(1 for r in flagged if r["is_fraud_label"])
        fp = len(flagged) - tp
        points.append(
            ThresholdPoint(
                threshold=t,
                alerts_flagged=len(flagged),
                precision=round(tp / len(flagged), 4) if flagged else 0.0,
                recall=round(tp / total_fraud, 4) if total_fraud else 0.0,
                fp_rate=round(fp / total_txns, 6),
            )
        )
        threshold += 0.05
    return points


@router.get("/rule-volume", response_model=list[RuleVolume])
def rule_volume(db: Session = Depends(get_db)):
    rows = db.execute(
        text(
            """
            select t.rule_name, count(*) as alert_count,
                   count(*) filter (where a.is_fraud_label) as true_positive_count
            from raw_marts_detection.fct_alert_rule_triggers t
            join raw_marts_detection.fct_alerts a using (alert_id)
            group by t.rule_name
            order by t.rule_name
            """
        )
    ).mappings().all()
    return [RuleVolume(**dict(r)) for r in rows]


@router.get("/threshold-recommendation", response_model=ThresholdRecommendation)
def threshold_recommendation(db: Session = Depends(get_db)):
    row = db.execute(
        text(
            """
            select recommended_threshold::float, dispositions_considered, computed_at
            from pipeline_state.threshold_recommendations
            order by recommendation_id desc limit 1
            """
        )
    ).mappings().first()
    if row is None:
        return ThresholdRecommendation(
            current_threshold=CURRENT_THRESHOLD,
            recommended_threshold=None,
            dispositions_considered=0,
            computed_at=None,
        )
    return ThresholdRecommendation(
        current_threshold=CURRENT_THRESHOLD,
        recommended_threshold=row["recommended_threshold"],
        dispositions_considered=row["dispositions_considered"],
        computed_at=row["computed_at"].isoformat() if row["computed_at"] else None,
    )
