"""Core ingestion logic for Apple Health data.

Processes metrics and workouts from Health Auto Export app
and writes them to InfluxDB.
"""

import logging
from datetime import datetime
from typing import Any

from dateutil import parser as date_parser
from influxdb_client import Point, WritePrecision
from influxdb_client.client.write_api import WriteApi

from .config import Config
from .models import METRIC_MAPPING, UNIT_MAPPING, SLEEP_FIELDS, HEART_RATE_FIELDS

logger = logging.getLogger(__name__)


def convert_units(value: float, from_unit: str, to_unit: str) -> float:
    """Convert between units.

    Args:
        value: The numeric value to convert.
        from_unit: Source unit (e.g., "kcal", "lb").
        to_unit: Target unit (e.g., "kJ", "kg").

    Returns:
        Converted value.
    """
    if from_unit == "kcal" and to_unit == "kJ":
        return value * 4.184
    if from_unit == "lb" and to_unit == "kg":
        return value * 0.453592
    return value


def parse_date(date_str: str) -> datetime:
    """Parse various date formats from Health Auto Export.

    Args:
        date_str: Date string in various formats.

    Returns:
        Parsed datetime object, or current UTC time if parsing fails.
    """
    try:
        return date_parser.parse(date_str)
    except Exception:
        logger.warning(f"Failed to parse date '{date_str}', using current time")
        return datetime.utcnow()


def sanitize_metric_name(name: str) -> str:
    """Convert metric names to snake_case.

    Args:
        name: Original metric name.

    Returns:
        Sanitized name in snake_case.
    """
    return name.lower().replace(" ", "_").replace("-", "_")


def get_entity_id(metric_name: str) -> str:
    """Get the entity_id for a metric.

    Args:
        metric_name: Original metric name from Health Auto Export.

    Returns:
        Mapped entity_id or generated fallback.
    """
    sanitized = sanitize_metric_name(metric_name)
    return METRIC_MAPPING.get(sanitized, f"applehealth_{sanitized}")


def get_unit_string(units: str) -> str:
    """Map units to standardized format.

    Args:
        units: Original unit string.

    Returns:
        Mapped unit string.
    """
    return UNIT_MAPPING.get(units, units)


def process_metrics(metrics: list[dict[str, Any]]) -> list[Point]:
    """Process health metrics into InfluxDB points.

    Args:
        metrics: List of metric dictionaries from Health Auto Export.

    Returns:
        List of InfluxDB Point objects.
    """
    points: list[Point] = []

    for metric in metrics:
        raw_name = metric.get("name", "unknown")
        entity_id = get_entity_id(raw_name)
        measurement = f"hae.{entity_id}"
        units = metric.get("units", "")
        unit_str = get_unit_string(units)

        for entry in metric.get("data", []):
            timestamp = parse_date(entry.get("date", ""))

            # Standard qty field
            if "qty" in entry:
                value = float(entry["qty"])

                # Convert units if needed
                if units == "kcal":
                    value = convert_units(value, "kcal", "kJ")
                    unit_str = "kJ"

                point = (
                    Point(measurement)
                    .tag("domain", "hae")
                    .tag("entity_id", entity_id)
                    .field("value", value)
                    .field("unit_of_measurement_str", unit_str)
                    .time(timestamp, WritePrecision.S)
                )
                points.append(point)

            # Heart Rate with Min/Avg/Max
            for key, suffix in HEART_RATE_FIELDS.items():
                if key in entry:
                    hr_entity_id = f"{entity_id}_{suffix}"
                    hr_measurement = f"hae.{hr_entity_id}"
                    point = (
                        Point(hr_measurement)
                        .tag("domain", "hae")
                        .tag("entity_id", hr_entity_id)
                        .field("value", float(entry[key]))
                        .field("unit_of_measurement_str", "bpm")
                        .time(timestamp, WritePrecision.S)
                    )
                    points.append(point)

            # Sleep Analysis - separate measurements for each sleep type
            for field, suffix in SLEEP_FIELDS.items():
                if field in entry:
                    sleep_entity_id = f"applehealth_sleep_analysis_{suffix}"
                    sleep_measurement = f"hae.{sleep_entity_id}"
                    point = (
                        Point(sleep_measurement)
                        .tag("domain", "hae")
                        .tag("entity_id", sleep_entity_id)
                        .field("value", float(entry[field]))
                        .field("unit_of_measurement_str", "min")
                        .time(timestamp, WritePrecision.S)
                    )
                    points.append(point)

    return points


def process_workouts(workouts: list[dict[str, Any]]) -> list[Point]:
    """Process workout data into InfluxDB points.

    Args:
        workouts: List of workout dictionaries from Health Auto Export.

    Returns:
        List of InfluxDB Point objects.
    """
    points: list[Point] = []

    for workout in workouts:
        workout_name = sanitize_metric_name(workout.get("name", "unknown"))
        timestamp = parse_date(workout.get("start", ""))

        # Workout Duration
        if "duration" in workout:
            entity_id = f"applehealth_workout_{workout_name}_duration"
            point = (
                Point(f"hae.{entity_id}")
                .tag("domain", "hae")
                .tag("entity_id", entity_id)
                .field("value", float(workout["duration"]) / 60.0)
                .field("unit_of_measurement_str", "min")
                .time(timestamp, WritePrecision.S)
            )
            points.append(point)

        # Active Energy
        if "activeEnergyBurned" in workout:
            energy = workout["activeEnergyBurned"]
            qty = float(energy.get("qty", 0)) if isinstance(energy, dict) else float(energy)
            entity_id = f"applehealth_workout_{workout_name}_energy"
            point = (
                Point(f"hae.{entity_id}")
                .tag("domain", "hae")
                .tag("entity_id", entity_id)
                .field("value", qty * 4.184)
                .field("unit_of_measurement_str", "kJ")
                .time(timestamp, WritePrecision.S)
            )
            points.append(point)

        # Distance
        if "distance" in workout:
            dist = workout["distance"]
            qty = float(dist.get("qty", 0)) if isinstance(dist, dict) else float(dist)
            entity_id = f"applehealth_workout_{workout_name}_distance"
            point = (
                Point(f"hae.{entity_id}")
                .tag("domain", "hae")
                .tag("entity_id", entity_id)
                .field("value", qty)
                .field("unit_of_measurement_str", "km")
                .time(timestamp, WritePrecision.S)
            )
            points.append(point)

    return points


def write_to_influxdb(
    write_api: WriteApi,
    points: list[Point],
    bucket: str | None = None,
    org: str | None = None,
) -> None:
    """Write points to InfluxDB with error handling.

    Args:
        write_api: InfluxDB write API instance.
        points: List of Point objects to write.
        bucket: Target bucket (defaults to config).
        org: Target org (defaults to config).

    Raises:
        Exception: If write fails after retries.
    """
    if not points:
        logger.debug("No points to write")
        return

    bucket = bucket or Config.INFLUXDB_BUCKET
    org = org or Config.INFLUXDB_ORG

    try:
        write_api.write(bucket=bucket, org=org, record=points)
        logger.debug(f"Successfully wrote {len(points)} points to InfluxDB")
    except Exception as e:
        logger.error(f"Failed to write to InfluxDB: {e}")
        raise
