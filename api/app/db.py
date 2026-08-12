from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

CREATE_APP_SCHEMA = """
create schema if not exists app;

create table if not exists app.alert_dispositions (
    disposition_id serial primary key,
    alert_id int not null,
    analyst_id varchar(64) not null,
    outcome varchar(32) not null check (outcome in ('true_positive', 'false_positive')),
    rationale_notes text not null,
    dispositioned_at timestamp not null default now(),
    unique (alert_id)
);

create table if not exists app.case_notes (
    note_id serial primary key,
    alert_id int not null,
    author varchar(64) not null,
    note_text text not null,
    created_at timestamp not null default now()
);

-- Owned by detection/evaluation/recompute_from_dispositions.py; the API only
-- ensures the table exists so /metrics/threshold-recommendation never 500s
-- before that script has run for the first time.
create schema if not exists pipeline_state;

create table if not exists pipeline_state.threshold_recommendations (
    recommendation_id serial primary key,
    recommended_threshold numeric(4, 2),
    dispositions_considered int not null,
    computed_at timestamp not null default now()
);
"""


def init_app_schema() -> None:
    with engine.begin() as conn:
        conn.execute(text(CREATE_APP_SCHEMA))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
