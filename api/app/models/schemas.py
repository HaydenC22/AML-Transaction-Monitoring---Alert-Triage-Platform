from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class AlertSummary(BaseModel):
    alert_id: int
    transaction_key: str
    transaction_type: str
    amount: float
    origin_account_nk: str
    severity: Literal["low", "medium", "high", "critical"]
    composite_score: float
    ml_anomaly_score: float
    is_fraud_label: bool
    created_at: datetime
    status: Literal["open", "closed"]
    rule_flags: list[str]


class AlertListResponse(BaseModel):
    items: list[AlertSummary]
    total: int
    page: int
    page_size: int


class TransactionContext(BaseModel):
    transaction_key: str
    day_offset: int
    transaction_type: str
    amount: float


class Disposition(BaseModel):
    disposition_id: int
    analyst_id: str
    outcome: Literal["true_positive", "false_positive"]
    rationale_notes: str
    dispositioned_at: datetime


class CaseNote(BaseModel):
    note_id: int
    author: str
    note_text: str
    created_at: datetime


class AlertDetail(AlertSummary):
    origin_geography_key: str | None
    dest_geography_key: str | None
    account_history: list[TransactionContext]
    disposition: Disposition | None
    notes: list[CaseNote]


class DispositionCreate(BaseModel):
    analyst_id: str = Field(min_length=1, max_length=64)
    outcome: Literal["true_positive", "false_positive"]
    rationale_notes: str = Field(min_length=1)


class CaseNoteCreate(BaseModel):
    author: str = Field(min_length=1, max_length=64)
    note_text: str = Field(min_length=1)


class OverviewMetrics(BaseModel):
    alert_volume_by_day: list[dict]
    fp_rate_trend: list[dict]
    severity_breakdown: list[dict]
    analyst_throughput_by_day: list[dict]
    latest_pipeline_run: dict | None


class TimelinePoint(BaseModel):
    day_offset: int
    transaction_count: int
    total_amount: float


class ThresholdPoint(BaseModel):
    threshold: float
    alerts_flagged: int
    precision: float
    recall: float
    fp_rate: float


class RuleVolume(BaseModel):
    rule_name: str
    alert_count: int
    true_positive_count: int


class ThresholdRecommendation(BaseModel):
    current_threshold: float
    recommended_threshold: float | None
    dispositions_considered: int
    computed_at: str | None
