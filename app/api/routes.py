"""HTTP routes for the manufacturing analytics service."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, Response

from app.config import get_settings
from app.graph import workflow as workflow_module
from app.schemas import (
    AnalysisDashboardResponse,
    AnalysisJob,
    AnalysisResponse,
    AnalyzeJsonRequest,
)
from app.tools.data_loader import load_production_data
from app.tools.pdf_report import build_report_filename, render_dashboard_pdf
from app.tools.presentation import build_dashboard_response

router = APIRouter(tags=["analysis"])
STATIC_DIR = Path(__file__).resolve().parents[1] / "static"
MAX_UPLOAD_BYTES = 2_000_000


@dataclass(frozen=True)
class ParsedAnalysisRequest:
    """Normalized request payload used by both API and UI routes."""

    job: AnalysisJob
    source_name: str | None


def _safe_source_name(value: str | None) -> str | None:
    if not value:
        return None
    name = Path(value).name.strip()
    return name or None


def _decode_csv_bytes(raw_bytes: bytes) -> str:
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="The uploaded CSV file is empty.")
    if len(raw_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail="The uploaded CSV file is too large for in-memory analysis.",
        )
    try:
        return raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="CSV uploads must be UTF-8 encoded.") from exc


async def _parse_analysis_request(request: Request) -> ParsedAnalysisRequest:
    """Normalize supported request shapes into a single `AnalysisJob`."""

    content_type = request.headers.get("content-type", "")
    settings = get_settings()

    if "multipart/form-data" in content_type:
        form = await request.form()
        upload = form.get("file")
        if upload is None or not hasattr(upload, "read"):
            raise HTTPException(
                status_code=400,
                detail="Upload a CSV file in the `file` field.",
            )

        csv_text = _decode_csv_bytes(await upload.read())
        source_name = _safe_source_name(getattr(upload, "filename", None))
        thread_id = str(form.get("thread_id") or uuid4())
        return ParsedAnalysisRequest(
            job=AnalysisJob(
                csv_text=csv_text,
                source_name=source_name,
                thread_id=thread_id,
                thresholds=settings.thresholds,
            ),
            source_name=source_name,
        )

    payload = AnalyzeJsonRequest.model_validate(await request.json())
    job = AnalysisJob.from_json_request(payload, thresholds=settings.thresholds)
    if not job.thread_id:
        job = job.model_copy(update={"thread_id": str(uuid4())})
    return ParsedAnalysisRequest(job=job, source_name=job.source_name)


def _run_analysis(job: AnalysisJob) -> AnalysisResponse:
    return AnalysisResponse.model_validate(workflow_module.run_workflow(job=job))


def _load_frame_for_job(job: AnalysisJob):
    return load_production_data(
        records=job.records,
        csv_text=job.csv_text,
        csv_path=job.csv_path,
    )


@router.get("/", include_in_schema=False)
async def web_console() -> FileResponse:
    """Serve the lightweight browser UI for manual analysis workflows."""

    return FileResponse(STATIC_DIR / "index.html")


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_production(request: Request) -> AnalysisResponse:
    """Analyze manufacturing telemetry from either JSON payloads or uploaded CSV files."""

    try:
        parsed = await _parse_analysis_request(request)
        return _run_analysis(parsed.job)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/analyze/dashboard", response_model=AnalysisDashboardResponse)
async def analyze_dashboard(request: Request) -> AnalysisDashboardResponse:
    """Analyze telemetry and return chart-ready summaries for the web UI."""

    try:
        parsed = await _parse_analysis_request(request)
        analysis_result = _run_analysis(parsed.job)
        frame = _load_frame_for_job(parsed.job)
        return build_dashboard_response(
            analysis_result=analysis_result,
            frame=frame,
            thresholds=parsed.job.thresholds,
            thread_id=parsed.job.thread_id or str(uuid4()),
            source_name=parsed.source_name,
        )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/reports/pdf")
async def download_dashboard_report(
    payload: AnalysisDashboardResponse,
) -> Response:
    """Return a downloadable PDF rendered from the dashboard payload."""

    pdf_bytes = render_dashboard_pdf(payload)
    filename = build_report_filename(payload.source_name)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
