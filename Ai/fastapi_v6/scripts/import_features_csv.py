from __future__ import annotations

import argparse
import csv
import json
import sqlite3
from datetime import datetime
from pathlib import Path

from app.db import init_db
from app.settings import settings


def _to_int(value: str | None, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(float(value))
    except Exception:
        return default


def _to_float(value: str | None, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except Exception:
        return default


def _sqlite_path(database_url: str) -> Path:
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        raise RuntimeError(
            f"This importer is SQLite-only. Current DATABASE_URL={database_url}"
        )
    return Path(database_url[len(prefix) :])


def import_csv(csv_path: Path) -> None:
    if not csv_path.exists():
        raise FileNotFoundError(csv_path)

    init_db()
    db_path = _sqlite_path(settings.database_url)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    now = datetime.utcnow().isoformat(timespec="seconds")

    sales_rows = []
    context_map: dict[str, tuple[float, float, int, int, int, int]] = {}
    training_rows = []

    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        required = {"date", "plu_code", "sales"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"missing required columns: {sorted(missing)}")

        for row in reader:
            d = (row.get("date") or "").strip()
            plu = (row.get("plu_code") or "").strip()
            if not d or not plu:
                continue

            sales_qty = _to_int(row.get("sales"), 0)
            sales_rows.append((d, plu, sales_qty, now))

            if d not in context_map:
                context_map[d] = (
                    _to_float(row.get("avg_temp_c"), 0.0),
                    _to_float(row.get("precipitation_mm"), 0.0),
                    _to_int(row.get("is_rain"), 0),
                    _to_int(row.get("is_holiday"), 0),
                    _to_int(row.get("academic_event"), 0),
                    _to_int(row.get("building_headcount"), 0),
                )

            features = {
                "lag_1": _to_float(row.get("lag_1"), 0.0),
                "lag_3": _to_float(row.get("lag_3"), 0.0),
                "lag_7": _to_float(row.get("lag_7"), 0.0),
                "rolling_7_mean": _to_float(row.get("rolling_7_mean"), 0.0),
                "rolling_7_std": _to_float(row.get("rolling_7_std"), 0.0),
                "day_of_week": _to_int(row.get("day_of_week"), 0),
                "month": _to_int(row.get("month"), 0),
                "is_holiday": _to_int(row.get("is_holiday"), 0),
                "academic_event": _to_int(row.get("academic_event"), 0),
                "avg_temp_c": _to_float(row.get("avg_temp_c"), 0.0),
                "precipitation_mm": _to_float(row.get("precipitation_mm"), 0.0),
                "is_rain": _to_int(row.get("is_rain"), 0),
                "building_headcount": _to_int(row.get("building_headcount"), 0),
                "safety_stock": _to_int(row.get("safety_stock"), 0),
                "category_l": (row.get("category_l") or "_unknown").strip() or "_unknown",
                "category_m": (row.get("category_m") or "_unknown").strip() or "_unknown",
                "category_s": (row.get("category_s") or "_unknown").strip() or "_unknown",
                "match_type": (row.get("match_type") or "").strip(),
            }
            training_rows.append((d, plu, json.dumps(features, ensure_ascii=False), sales_qty, now, now))

    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")

        conn.executemany(
            """
            INSERT INTO daily_sales (sales_date, plu_code, sales_qty, ingested_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(sales_date, plu_code)
            DO UPDATE SET sales_qty=excluded.sales_qty, ingested_at=excluded.ingested_at
            """,
            sales_rows,
        )

        context_rows = [
            (d, v[0], v[1], v[2], v[3], v[4], v[5], now)
            for d, v in sorted(context_map.items())
        ]
        conn.executemany(
            """
            INSERT INTO daily_context
            (target_date, avg_temp_c, precipitation_mm, is_rain, is_holiday, academic_event, building_headcount, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(target_date)
            DO UPDATE SET
                avg_temp_c=excluded.avg_temp_c,
                precipitation_mm=excluded.precipitation_mm,
                is_rain=excluded.is_rain,
                is_holiday=excluded.is_holiday,
                academic_event=excluded.academic_event,
                building_headcount=excluded.building_headcount,
                updated_at=excluded.updated_at
            """,
            context_rows,
        )

        conn.executemany(
            """
            INSERT INTO training_dataset
            (target_date, plu_code, features, target_sales, labeled_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(target_date, plu_code)
            DO UPDATE SET
                features=excluded.features,
                target_sales=excluded.target_sales,
                labeled_at=excluded.labeled_at
            """,
            training_rows,
        )
        conn.commit()

    print(f"import done: {csv_path}")
    print(f"daily_sales upsert: {len(sales_rows)}")
    print(f"daily_context upsert: {len(context_map)}")
    print(f"training_dataset upsert: {len(training_rows)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Import feature CSV into FastAPI v6 SQLite DB")
    parser.add_argument("--csv", required=True, help="absolute csv path")
    args = parser.parse_args()

    import_csv(Path(args.csv).expanduser().resolve())


if __name__ == "__main__":
    main()
