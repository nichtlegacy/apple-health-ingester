"""Apple Health Ingester - FastAPI Application.

Receives JSON data from Health Auto Export iOS app
and writes it to InfluxDB.
"""

import logging
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.responses import JSONResponse
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS

from .config import Config, setup_logging
from .ingester import process_metrics, process_workouts, write_to_influxdb

# Setup logging before anything else
setup_logging()
logger = logging.getLogger(__name__)

# Global InfluxDB client and write API
influx_client: Optional[InfluxDBClient] = None
write_api = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown."""
    global influx_client, write_api

    # Startup
    logger.info("Starting Apple Health Ingester...")

    if not Config.validate():
        logger.error("Configuration validation failed. Check environment variables.")
        raise SystemExit(1)

    Config.log_config()

    try:
        influx_client = InfluxDBClient(
            url=Config.INFLUXDB_URL,
            token=Config.INFLUXDB_TOKEN,
            org=Config.INFLUXDB_ORG,
        )
        # Test connection
        health = influx_client.health()
        if health.status != "pass":
            raise ConnectionError(f"InfluxDB health check failed: {health.message}")

        write_api = influx_client.write_api(write_options=SYNCHRONOUS)
        logger.info(f"Connected to InfluxDB at {Config.INFLUXDB_URL}")

    except Exception as e:
        logger.error(f"Failed to connect to InfluxDB: {e}")
        raise SystemExit(1)

    yield

    # Shutdown
    logger.info("Shutting down Apple Health Ingester...")
    if influx_client:
        influx_client.close()
        logger.info("InfluxDB connection closed")


app = FastAPI(
    title="Apple Health Ingester",
    version="2.0.0",
    description="Ingests health data from Health Auto Export iOS app into InfluxDB",
    lifespan=lifespan,
)


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "status": "ok",
        "service": "Apple Health Ingester",
        "version": "1.0.0",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for container orchestration."""
    if not influx_client or not write_api:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "reason": "InfluxDB not connected"},
        )
    return {"status": "healthy"}


@app.post("/")
@app.post("/api/healthdata")
@app.post("/ingest")
async def ingest_health_data(
    request: Request,
    authorization: Optional[str] = Header(None),
):
    """Receive health data and write to InfluxDB.

    Accepts JSON payload from Health Auto Export iOS app and writes
    metrics and workouts to InfluxDB.
    """
    request_id = str(uuid.uuid4())[:8]

    # API Key authentication (if configured)
    if Config.API_KEY:
        if not authorization:
            logger.warning(f"[{request_id}] Request rejected: missing authorization header")
            raise HTTPException(
                status_code=401,
                detail={
                    "status": "error",
                    "error_code": "MISSING_AUTHORIZATION",
                    "message": "Authorization header required",
                },
            )
        token = authorization.replace("Bearer ", "").strip()
        if token != Config.API_KEY:
            logger.warning(f"[{request_id}] Request rejected: invalid API key")
            raise HTTPException(
                status_code=403,
                detail={
                    "status": "error",
                    "error_code": "INVALID_API_KEY",
                    "message": "Invalid API key",
                },
            )

    # Check InfluxDB connection
    if not write_api:
        logger.error(f"[{request_id}] InfluxDB not connected")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "error",
                "error_code": "INFLUXDB_NOT_CONNECTED",
                "message": "InfluxDB connection not available",
            },
        )

    # Parse JSON payload
    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"[{request_id}] Failed to parse JSON: {e}")
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "error_code": "INVALID_JSON",
                "message": "Failed to parse JSON payload",
                "details": str(e),
            },
        )

    # Extract data
    data = payload.get("data", payload)
    metrics = data.get("metrics", [])
    workouts = data.get("workouts", [])

    logger.debug(f"[{request_id}] Processing {len(metrics)} metrics, {len(workouts)} workouts")

    # Process metrics and workouts
    metric_points = process_metrics(metrics)
    workout_points = process_workouts(workouts)
    all_points = metric_points + workout_points

    # Write to InfluxDB
    if all_points:
        try:
            write_to_influxdb(write_api, all_points)
            logger.info(
                f"[{request_id}] Written: {len(metric_points)} metrics, "
                f"{len(workout_points)} workouts, {len(all_points)} points total"
            )
        except Exception as e:
            logger.error(f"[{request_id}] InfluxDB write failed: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "status": "error",
                    "error_code": "INFLUXDB_WRITE_ERROR",
                    "message": "Failed to write data to InfluxDB",
                    "details": str(e),
                },
            )
    else:
        logger.info(f"[{request_id}] No data points to write")

    return JSONResponse(
        status_code=200,
        content={
            "status": "success",
            "request_id": request_id,
            "metrics_imported": len(metric_points),
            "workouts_imported": len(workouts),
            "points_written": len(all_points),
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=Config.PORT)
