"""Chat, plan, and execute endpoints."""

from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse

from dta.dti.coe.orchestrator import orchestrate
from dta.dti.executor import PipelineExecutor
from dta.dti.schemas import ChatRequest as COEChatRequest

from ..schemas import ChatRequest, ErrorCode, ErrorDetail, ErrorResponse
from ..utils import sse_frame

router = APIRouter(prefix="/v1", tags=["chat"])


@router.post("/plan")  # type: ignore[misc]
async def create_plan(req: ChatRequest) -> JSONResponse:
    try:
        if not req.messages:
            raise HTTPException(status_code=400, detail="No messages provided")

        prompt = req.messages[-1].content
        coe_req = COEChatRequest(prompt=prompt, attachments=[])

        result = orchestrate(coe_req)

        if not result.get("ok"):
            details = {}
            if result.get("candidate"):
                details["candidate"] = result.get("candidate")

            return JSONResponse(
                status_code=400,
                content=ErrorResponse(
                    error=ErrorDetail(
                        code=ErrorCode.BAD_REQUEST,
                        message=str(result.get("error", "Plan generation failed")),
                        details=details if details else None,
                    )
                ).model_dump(exclude_none=True),
            )

        return JSONResponse(
            {
                "ok": True,
                "plan": result["plan"],
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Plan generation failed: {e}") from e


@router.post("/execute")  # type: ignore[misc]
async def execute_plan(req: ChatRequest) -> JSONResponse:
    try:
        if not req.messages:
            raise HTTPException(status_code=400, detail="No messages provided")

        prompt = req.messages[-1].content
        coe_req = COEChatRequest(prompt=prompt, attachments=[])

        orch_result = orchestrate(coe_req)

        if not orch_result.get("ok"):
            details = {}
            if orch_result.get("candidate"):
                details["candidate"] = orch_result.get("candidate")

            return JSONResponse(
                status_code=400,
                content=ErrorResponse(
                    error=ErrorDetail(
                        code=ErrorCode.BAD_REQUEST,
                        message=str(orch_result.get("error", "Plan generation failed")),
                        details=details if details else None,
                    )
                ).model_dump(exclude_none=True),
            )

        plan_dict = orch_result["plan"]

        from dta.dti.schemas import ExecutionPlan

        plan = ExecutionPlan(**plan_dict)
        executor = PipelineExecutor()

        progress_events: list[dict[str, Any]] = []

        def on_progress(event: dict[str, Any]) -> None:
            progress_events.append(event)

        exec_result = executor.execute(plan, on_progress=on_progress)

        return JSONResponse(
            {
                "ok": True,
                "plan": plan_dict,
                "result": exec_result,
                "progress": progress_events,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Execution failed: {e}") from e


@router.post("/chat")  # type: ignore[misc]
async def chat(req: ChatRequest) -> StreamingResponse:
    async def gen() -> AsyncIterator[bytes]:
        try:
            if not req.messages:
                err = ErrorResponse(error=ErrorDetail(code=ErrorCode.BAD_REQUEST, message="No messages provided"))
                yield sse_frame(err.model_dump(exclude_none=True))
                yield sse_frame({"done": True})
                return

            prompt = req.messages[-1].content
            coe_req = COEChatRequest(prompt=prompt, attachments=[])

            yield sse_frame({"event": "planning", "message": "Generating execution plan..."})

            orch_result = orchestrate(coe_req)

            if not orch_result.get("ok"):
                details = {}
                if orch_result.get("candidate"):
                    details["candidate"] = orch_result.get("candidate")

                err = ErrorResponse(
                    error=ErrorDetail(
                        code=ErrorCode.BAD_REQUEST,
                        message=str(orch_result.get("error", "Planning failed")),
                        details=details if details else None,
                    )
                )
                yield sse_frame(err.model_dump(exclude_none=True))
                yield sse_frame({"done": True})
                return

            yield sse_frame({"event": "plan_ready", "plan": orch_result["plan"]})

            from dta.dti.schemas import ExecutionPlan

            plan = ExecutionPlan(**orch_result["plan"])
            executor = PipelineExecutor()

            def on_progress(event: dict[str, Any]) -> None:
                pass

            yield sse_frame({"event": "executing", "message": "Running pipeline..."})

            exec_result = executor.execute(plan, on_progress=on_progress)

            yield sse_frame({"event": "complete", "result": exec_result})
            yield sse_frame({"done": True})

        except Exception as e:
            err = ErrorResponse(error=ErrorDetail(code=ErrorCode.INTERNAL_ERROR, message=str(e)))
            yield sse_frame(err.model_dump(exclude_none=True))
            yield sse_frame({"done": True})

    return StreamingResponse(gen(), media_type="text/event-stream")
