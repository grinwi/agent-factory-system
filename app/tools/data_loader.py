"""Helpers for loading and normalizing manufacturing telemetry."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from io import StringIO
from pathlib import Path
from typing import Any

import pandas as pd
from pydantic import BaseModel

from app.schemas import PlantSnapshot

REQUIRED_COLUMNS = (
    "machine_id",
    "temperature",
    "error_rate",
    "downtime_minutes",
)
OPTIONAL_COLUMNS = (
    "line_id",
    "station_id",
    "shift",
    "planned_production_minutes",
    "good_units",
    "reject_units",
    "ideal_cycle_time_seconds",
)
NUMERIC_OPTIONAL_COLUMNS = (
    "planned_production_minutes",
    "good_units",
    "reject_units",
    "ideal_cycle_time_seconds",
)


class DataFormatError(ValueError):
    """Raised when input telemetry is missing required fields or values."""


def _coerce_records(records: Sequence[Mapping[str, Any] | BaseModel]) -> list[dict[str, Any]]:
    normalized_records: list[dict[str, Any]] = []
    for record in records:
        if isinstance(record, BaseModel):
            normalized_records.append(record.model_dump(mode="json"))
        else:
            normalized_records.append(dict(record))
    return normalized_records


def normalize_dataframe(frame: pd.DataFrame) -> pd.DataFrame:
    """Validate column presence and normalize types for downstream analysis."""

    missing_columns = sorted(set(REQUIRED_COLUMNS) - set(frame.columns))
    if missing_columns:
        raise DataFormatError(
            "Missing required production columns: " + ", ".join(missing_columns)
        )

    selected_columns = list(REQUIRED_COLUMNS) + [
        column for column in OPTIONAL_COLUMNS if column in frame.columns
    ]
    normalized = frame.loc[:, selected_columns].copy()
    normalized["machine_id"] = normalized["machine_id"].astype(str)

    for column in ("temperature", "error_rate", "downtime_minutes"):
        normalized[column] = pd.to_numeric(normalized[column], errors="raise")
    for column in NUMERIC_OPTIONAL_COLUMNS:
        if column in normalized.columns:
            normalized[column] = pd.to_numeric(normalized[column], errors="raise")

    return normalized


def load_production_data(
    *,
    records: Sequence[Mapping[str, Any] | BaseModel] | None = None,
    csv_text: str | None = None,
    csv_path: str | Path | None = None,
    file_path: str | Path | None = None,
    path: str | Path | None = None,
) -> pd.DataFrame:
    """Load production data from JSON-like records, CSV text, or a CSV file path."""

    if records:
        frame = pd.DataFrame(_coerce_records(records))
    elif csv_text:
        frame = pd.read_csv(StringIO(csv_text))
    else:
        source_path = csv_path or file_path or path
        if source_path is None:
            raise DataFormatError("No production data source was provided.")
        frame = pd.read_csv(source_path)

    return normalize_dataframe(frame)


def dataframe_to_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    """Return JSON-serializable row dictionaries."""

    return normalize_dataframe(frame).to_dict(orient="records")


def build_plant_snapshot(frame: pd.DataFrame) -> PlantSnapshot:
    """Create a plant summary used by reasoning and validation agents."""

    normalized = normalize_dataframe(frame)
    return PlantSnapshot(
        record_count=int(len(normalized)),
        machine_count=int(normalized["machine_id"].nunique()),
        average_temperature=round(float(normalized["temperature"].mean()), 2),
        average_error_rate=round(float(normalized["error_rate"].mean()), 4),
        total_downtime_minutes=round(float(normalized["downtime_minutes"].sum()), 2),
        max_temperature=round(float(normalized["temperature"].max()), 2),
        max_error_rate=round(float(normalized["error_rate"].max()), 4),
        max_downtime_minutes=round(float(normalized["downtime_minutes"].max()), 2),
    )
