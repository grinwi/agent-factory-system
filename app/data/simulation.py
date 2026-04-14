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
    """Generate a realistic production telemetry snapshot with injected anomalies."""

    rng = Random(seed)
    rows: list[dict[str, float | str]] = []

    anomaly_indices = {8, 15, 23}
    for index in range(machine_count):
        machine_id = f"M-{index + 1:03d}"
        temperature = round(rng.uniform(71.0, 77.5), 1)
        error_rate = round(rng.uniform(0.008, 0.015), 3)
        downtime = round(rng.uniform(2, 8), 0)

        if index in anomaly_indices:
            temperature = round(rng.uniform(96.0, 102.0), 1)
            error_rate = round(rng.uniform(0.038, 0.055), 3)
            downtime = round(rng.uniform(42, 56), 0)

        rows.append(
            {
                "machine_id": machine_id,
                "temperature": temperature,
                "error_rate": error_rate,
                "downtime_minutes": downtime,
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

