from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.schemas import (
    AlertDetail,
    AlertListResponse,
    AlertSummary,
    CaseNote,
    CaseNoteCreate,
    Disposition,
    DispositionCreate,
    TransactionContext,
)

router = APIRouter(prefix="/alerts", tags=["alerts"])

LIST_QUERY_BASE = """
select
    a.alert_id, a.transaction_key, a.transaction_type, a.amount::float as amount,
    a.origin_account_nk, a.severity, a.composite_score::float as composite_score,
    a.ml_anomaly_score::float as ml_anomaly_score, a.is_fraud_label, a.created_at,
    case when d.disposition_id is null then 'open' else 'closed' end as status,
    coalesce(
        (select array_agg(rule_name) from raw_marts_detection.fct_alert_rule_triggers t
         where t.alert_id = a.alert_id),
        array[]::text[]
    ) as rule_flags
from raw_marts_detection.fct_alerts a
left join app.alert_dispositions d on d.alert_id = a.alert_id
"""


@router.get("", response_model=AlertListResponse)
def list_alerts(
    db: Session = Depends(get_db),
    status: str | None = Query(default=None, pattern="^(open|closed)$"),
    severity: str | None = Query(default=None, pattern="^(low|medium|high|critical)$"),
    rule: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
):
    where_clauses = []
    params: dict = {}

    if status == "open":
        where_clauses.append("d.disposition_id is null")
    elif status == "closed":
        where_clauses.append("d.disposition_id is not null")
    if severity:
        where_clauses.append("a.severity = :severity")
        params["severity"] = severity
    if rule:
        where_clauses.append(
            "exists (select 1 from raw_marts_detection.fct_alert_rule_triggers t "
            "where t.alert_id = a.alert_id and t.rule_name = :rule)"
        )
        params["rule"] = rule

    where_sql = f"where {' and '.join(where_clauses)}" if where_clauses else ""

    count_sql = f"select count(*) from ({LIST_QUERY_BASE} {where_sql}) sub"
    total = db.execute(text(count_sql), params).scalar_one()

    list_sql = (
        f"{LIST_QUERY_BASE} {where_sql} "
        "order by a.composite_score desc, a.created_at desc "
        "limit :limit offset :offset"
    )
    params["limit"] = page_size
    params["offset"] = (page - 1) * page_size
    rows = db.execute(text(list_sql), params).mappings().all()

    return AlertListResponse(
        items=[AlertSummary(**dict(row)) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{alert_id}", response_model=AlertDetail)
def get_alert(alert_id: int, db: Session = Depends(get_db)):
    row = db.execute(
        text(
            f"{LIST_QUERY_BASE} where a.alert_id = :alert_id"
        ),
        {"alert_id": alert_id},
    ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Alert not found")

    geo = db.execute(
        text(
            """
            select origin_geography_key::text, dest_geography_key::text
            from raw_marts_core.fact_transactions
            where transaction_key = :tk
            """
        ),
        {"tk": row["transaction_key"]},
    ).mappings().first()

    history_rows = db.execute(
        text(
            """
            select f.transaction_key, d.simulated_day_offset as day_offset,
                   f.transaction_type, f.amount::float as amount
            from raw_marts_core.fact_transactions f
            join raw_marts_core.dim_account a on a.account_key = f.origin_account_key
            join raw_marts_core.dim_date d on d.date_key = f.date_key
            where a.account_nk = :account_nk
            order by d.simulated_day_offset desc, f.hour_of_day desc
            limit 10
            """
        ),
        {"account_nk": row["origin_account_nk"]},
    ).mappings().all()

    disposition_row = db.execute(
        text(
            """
            select disposition_id, analyst_id, outcome, rationale_notes, dispositioned_at
            from app.alert_dispositions where alert_id = :alert_id
            """
        ),
        {"alert_id": alert_id},
    ).mappings().first()

    note_rows = db.execute(
        text(
            """
            select note_id, author, note_text, created_at
            from app.case_notes where alert_id = :alert_id
            order by created_at asc
            """
        ),
        {"alert_id": alert_id},
    ).mappings().all()

    return AlertDetail(
        **dict(row),
        origin_geography_key=geo["origin_geography_key"] if geo else None,
        dest_geography_key=geo["dest_geography_key"] if geo else None,
        account_history=[TransactionContext(**dict(r)) for r in history_rows],
        disposition=Disposition(**dict(disposition_row)) if disposition_row else None,
        notes=[CaseNote(**dict(r)) for r in note_rows],
    )


@router.post("/{alert_id}/disposition", response_model=Disposition, status_code=201)
def disposition_alert(alert_id: int, payload: DispositionCreate, db: Session = Depends(get_db)):
    exists = db.execute(
        text("select 1 from raw_marts_detection.fct_alerts where alert_id = :alert_id"),
        {"alert_id": alert_id},
    ).first()
    if exists is None:
        raise HTTPException(status_code=404, detail="Alert not found")

    already = db.execute(
        text("select 1 from app.alert_dispositions where alert_id = :alert_id"),
        {"alert_id": alert_id},
    ).first()
    if already is not None:
        raise HTTPException(status_code=409, detail="Alert already dispositioned")

    row = db.execute(
        text(
            """
            insert into app.alert_dispositions (alert_id, analyst_id, outcome, rationale_notes)
            values (:alert_id, :analyst_id, :outcome, :rationale_notes)
            returning disposition_id, analyst_id, outcome, rationale_notes, dispositioned_at
            """
        ),
        {"alert_id": alert_id, **payload.model_dump()},
    ).mappings().first()
    db.commit()
    return Disposition(**dict(row))


@router.post("/{alert_id}/notes", response_model=CaseNote, status_code=201)
def add_note(alert_id: int, payload: CaseNoteCreate, db: Session = Depends(get_db)):
    exists = db.execute(
        text("select 1 from raw_marts_detection.fct_alerts where alert_id = :alert_id"),
        {"alert_id": alert_id},
    ).first()
    if exists is None:
        raise HTTPException(status_code=404, detail="Alert not found")

    row = db.execute(
        text(
            """
            insert into app.case_notes (alert_id, author, note_text)
            values (:alert_id, :author, :note_text)
            returning note_id, author, note_text, created_at
            """
        ),
        {"alert_id": alert_id, **payload.model_dump()},
    ).mappings().first()
    db.commit()
    return CaseNote(**dict(row))
