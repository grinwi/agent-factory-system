"""HTTP routes for the manufacturing analytics service."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.config import get_settings
from app.graph import workflow as workflow_module
from app.schemas import AnalysisJob, AnalysisResponse, AnalyzeJsonRequest


router = APIRouter(tags=["analysis"])


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_production(request: Request) -> AnalysisResponse:
    """Analyze manufacturing telemetry from either JSON payloads or uploaded CSV files."""

    content_type = request.headers.get("content-type", "")

    try:
        if "multipart/form-data" in content_type:
            form = await request.form()
            upload = form.get("file")
            if upload is None or not hasattr(upload, "read"):
                raise HTTPException(status_code=400, detail="Upload a CSV file in the `file` field.")

            raw_bytes = await upload.read()
            if not raw_bytes:
                raise HTTPException(status_code=400, detail="The uploaded CSV file is empty.")

            thread_id = form.get("thread_id")
            result = workflow_module.run_workflow(
                csv_text=raw_bytes.decode("utf-8"),
                thread_id=str(thread_id) if thread_id else None,
                state={"source_name": getattr(upload, "filename", None)},
            )
            return AnalysisResponse.model_validate(result)

        payload = AnalyzeJsonRequest.model_validate(await request.json())
        job = AnalysisJob.from_json_request(payload, thresholds=get_settings().thresholds)
        result = workflow_module.run_workflow(job=job)
        return AnalysisResponse.model_validate(result)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
