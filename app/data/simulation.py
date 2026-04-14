"""Generate synthetic production data with realistic anomalies."""

from __future__ import annotations

from pathlib import Path
from random import Random

import pandas as pd


def generate_sample_production_data(
    *,
    machine_count: int = 30,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate telemetry with optional automotive-style OEE columns and anomalies."""

    rng = Random(seed)
    rows: list[dict[str, float | str]] = []
    line_names = ("Body-01", "Paint-02", "Assembly-03")
    shift_names = ("A", "B", "C")

    anomaly_indices = {8, 15, 23}
    for index in range(machine_count):
        machine_id = f"M-{index + 1:03d}"
        line_id = line_names[min(index // 10, len(line_names) - 1)]
        shift = shift_names[index % len(shift_names)]
        station_id = f"{line_id}-ST{(index % 10) + 1:02d}"
        planned_production_minutes = 480.0
        temperature = round(rng.uniform(71.0, 77.5), 1)
        error_rate = round(rng.uniform(0.008, 0.015), 3)
        downtime = round(rng.uniform(2, 8), 0)
        ideal_cycle_time_seconds = round(rng.uniform(52.0, 68.0), 1)
        performance_factor = rng.uniform(0.87, 0.97)
        quality_factor = rng.uniform(0.985, 0.997)

        if index in anomaly_indices:
            temperature = round(rng.uniform(96.0, 102.0), 1)
            error_rate = round(rng.uniform(0.038, 0.055), 3)
            downtime = round(rng.uniform(42, 56), 0)
            performance_factor = rng.uniform(0.68, 0.8)
            quality_factor = rng.uniform(0.91, 0.96)

        operating_minutes = max(planned_production_minutes - downtime, 0)
        theoretical_units = (
            operating_minutes * 60 / ideal_cycle_time_seconds if operating_minutes else 0
        )
        total_units = max(int(theoretical_units * performance_factor), 1)
        good_units = max(int(total_units * quality_factor), 0)
        reject_units = max(total_units - good_units, 0)

        rows.append(
            {
                "machine_id": machine_id,
                "line_id": line_id,
                "station_id": station_id,
                "shift": shift,
                "temperature": temperature,
                "error_rate": error_rate,
                "downtime_minutes": downtime,
                "planned_production_minutes": planned_production_minutes,
                "good_units": good_units,
                "reject_units": reject_units,
                "ideal_cycle_time_seconds": ideal_cycle_time_seconds,
            }
        )

    return pd.DataFrame(rows)


def save_sample_dataset(
    destination: str | Path = "data/production_sample.csv",
    *,
    machine_count: int = 30,
    seed: int = 42,
) -> Path:
    """Persist a generated sample dataset to disk."""

    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    generate_sample_production_data(machine_count=machine_count, seed=seed).to_csv(
        path, index=False
    )
    return path


if __name__ == "__main__":
    saved_path = save_sample_dataset()
    print(f"Saved sample production data to {saved_path}")
