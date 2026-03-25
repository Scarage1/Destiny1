from __future__ import annotations

import hashlib
import json
import socket
import time
import uuid
from typing import Any

import google.generativeai as genai

from .executor_agent import execute_sql
from .guard_agent import guard
from .intent_schema import validate_and_normalize_plan
from .llm_client import GroqModel as _GroqModel
from .memory import get_context, update_context
from .observability import build_agent_trace_summary, log_event
from .planner_agent import plan as planner_plan
from .query_agent import generate_sql
from .response_agent import synthesize
from .runtime_config import RuntimeConfig, get_runtime_config
from .validator_agent import validate_plan_for_execution
from .verifier_agent import verify

try:
    from ..guardrails import REJECTION_RESPONSE, normalize_user_query
except ImportError:
    from guardrails import REJECTION_RESPONSE, normalize_user_query


GEMINI_HOST = "generativelanguage.googleapis.com"



def _get_model():
    runtime_config = get_runtime_config()
    gemini_api_key = runtime_config.gemini_api_key
    if not gemini_api_key or not _can_resolve_gemini_host():
        return None
    genai.configure(api_key=gemini_api_key)
    return genai.GenerativeModel("gemini-2.0-flash")


def _get_fallback_model():
    runtime_config = get_runtime_config()
    groq_api_key = runtime_config.groq_api_key
    groq_model = runtime_config.groq_model
    if not groq_api_key:
        return None
    return _GroqModel(groq_api_key, groq_model)


def _can_resolve_gemini_host(timeout_seconds: float = 2.0) -> bool:
    """Fast DNS reachability probe for Gemini endpoint."""
    previous_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(timeout_seconds)
    try:
        socket.getaddrinfo(GEMINI_HOST, 443)
        return True
    except OSError:
        return False
    finally:
        socket.setdefaulttimeout(previous_timeout)


def _resolve_reasoning_model(trace_id: str, config: RuntimeConfig) -> Any | None:
    if config.strict_deterministic:
        log_event(trace_id, "llm_disabled_strict_mode", {"reason": "O2C_STRICT_DETERMINISTIC enabled"})
        return None

    model = _get_model()
    if model is not None:
        return model

    fallback_model = _get_fallback_model()
    if fallback_model is not None:
        log_event(trace_id, "llm_fallback_selected", {"provider": "groq", "stage": "reasoning"})
    return fallback_model



def _friendly_llm_error(exc: Exception) -> str:
    """Convert raw LLM errors into user-friendly messages."""
    msg = str(exc).lower()
    if any(x in msg for x in ("429", "quota", "rate limit", "resource_exhausted", "llm providers are temporarily")):
        return (
            "Our analytics engine is currently experiencing high demand. "
            "Your data is being queried using built-in templates. "
            "Please try again in a moment if the result is incomplete."
        )
    if "timeout" in msg or "timed out" in msg:
        return (
            "The query took too long to generate. "
            "Try a more specific question, for example mentioning the exact document ID."
        )
    if "unavailable" in msg or "connection" in msg:
        return (
            "The AI reasoning engine is temporarily offline. "
            "Built-in templates are still active for common O2C queries."
        )
    return (
        "We couldn't generate a query for that question right now. "
        "Try rephrasing, or use one of the example queries below."
    )


def process_query(user_query: str, conversation_id: str | None = None) -> dict[str, Any]:
    """Deterministic orchestration: plan → validate → guard → query → execute → verify → respond."""
    runtime_config = get_runtime_config()
    pipeline_timeout_ms = runtime_config.pipeline_timeout_ms
    stage_budget_ms = runtime_config.stage_budget_ms
    llm_timeout_seconds = runtime_config.llm_timeout_seconds

    normalized_query = normalize_user_query(user_query)
    trace_id = str(uuid.uuid4())
    conversation_id = conversation_id or str(uuid.uuid4())
    llm_used = False
    llm_provider: str | None = None
    context = get_context(conversation_id)
    pipeline_started = time.perf_counter()
    stage_latencies_ms: dict[str, int] = {}
    budget_warnings: list[str] = []

    def _elapsed_pipeline_ms() -> int:
        return int((time.perf_counter() - pipeline_started) * 1000)

    def _remaining_pipeline_ms() -> int:
        return max(0, pipeline_timeout_ms - _elapsed_pipeline_ms())

    def _record_stage_latency(stage: str, started_at: float) -> int:
        elapsed = int((time.perf_counter() - started_at) * 1000)
        stage_latencies_ms[stage] = elapsed
        budget = stage_budget_ms.get(stage)
        within_budget = budget is None or elapsed <= budget
        if budget is not None and not within_budget:
            budget_warnings.append(f"Stage '{stage}' exceeded budget ({elapsed}ms > {budget}ms)")
        log_event(
            trace_id,
            "stage_latency",
            {
                "stage": stage,
                "elapsed_ms": elapsed,
                "budget_ms": budget,
                "within_budget": within_budget,
            },
        )
        return elapsed

    def _pipeline_timed_out() -> bool:
        return _elapsed_pipeline_ms() > pipeline_timeout_ms

    def _agent_trace(
        intent_plan: dict[str, Any] | None,
        sql: str | None,
        verification: dict[str, Any] | None,
        clarification: str | None,
        row_count: int | None,
    ) -> dict[str, Any]:
        return build_agent_trace_summary(
            trace_id=trace_id,
            intent_plan=intent_plan,
            sql=sql,
            verification=verification,
            clarification=clarification,
            row_count=row_count,
            llm_used=llm_used,
            llm_provider=llm_provider,
            stage_latencies_ms=stage_latencies_ms,
        )

    def _make_result(
        *,
        answer: str,
        status: str,
        plan: dict[str, Any] | None = None,
        sql: str | None = None,
        results: list[dict[str, Any]] | None = None,
        referenced_nodes: list[str] | None = None,
        verification: dict[str, Any] | None = None,
        clarification: str | None = None,
        row_count: int | None = None,
    ) -> dict[str, Any]:
        """Single factory for the pipeline result dict — eliminates 10x boilerplate."""
        v = verification or {"status": "skipped", "warnings": []}
        return {
            "answer": answer,
            "query": sql,
            "results": results,
            "result_columns": list(results[0].keys()) if results else None,
            "total_results": len(results) if results is not None else None,
            "referenced_nodes": referenced_nodes or [],
            "status": status,
            "trace_id": trace_id,
            "conversation_id": conversation_id,
            "intent": plan.get("intent") if plan else None,
            "plan": plan,
            "verification": v,
            "agent_trace": _agent_trace(plan, sql, v, clarification, row_count),
        }

    log_event(trace_id, "request", {"query": normalized_query, "conversation_id": conversation_id})

    def _query_fingerprint(query: str, plan_payload: dict[str, Any] | None = None) -> str:
        base = {
            "query": query,
            "plan": plan_payload or {},
        }
        raw = json.dumps(base, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]

    if not normalized_query:
        return _make_result(
            answer="Query cannot be empty.",
            status="rejected",
            verification={"status": "skipped", "warnings": ["Empty query"]},
        )

    if len(normalized_query) > 2000:
        return _make_result(
            answer="Query is too long. Please keep it under 2000 characters.",
            status="rejected",
            verification={"status": "skipped", "warnings": ["Query too long"]},
        )

    reasoning_model = _resolve_reasoning_model(trace_id, runtime_config)
    if reasoning_model is not None:
        llm_provider = getattr(reasoning_model, "provider", "gemini")
        llm_used = True

    stage_started = time.perf_counter()
    raw_plan = planner_plan(
        normalized_query,
        context,
        reasoning_model,
        trace_id,
        llm_timeout_seconds=max(0.1, min(llm_timeout_seconds, _remaining_pipeline_ms() / 1000)),
    )
    _record_stage_latency("planner", stage_started)
    try:
        plan = validate_and_normalize_plan(raw_plan)
    except ValueError as e:
        clarification_msg = (
            "I need clarification before running this query. "
            "Please specify the entity and metric you want."
        )
        log_event(trace_id, "clarification", {"reason": str(e), "question": clarification_msg})
        return _make_result(
            answer=clarification_msg,
            status="clarification",
            verification={"status": "skipped", "warnings": ["Clarification required"]},
            clarification=clarification_msg,
        )

    if _pipeline_timed_out():
        reason = "Request timed out while processing. Please narrow the query and try again."
        log_event(
            trace_id,
            "pipeline_timeout",
            {"elapsed_ms": _elapsed_pipeline_ms(), "timeout_ms": pipeline_timeout_ms},
        )
        return _make_result(
            answer=reason,
            status="error",
            plan=plan,
            verification={"status": "failed", "warnings": [reason]},
        )

    clarification_msg = plan.get("clarification")
    confidence = float(plan.get("confidence", 1.0))
    query_fingerprint = _query_fingerprint(normalized_query, plan)
    log_event(trace_id, "query_fingerprint", {"fingerprint": query_fingerprint})
    if clarification_msg and confidence < 0.7:
        update_context(conversation_id, plan, trace_id, pending_clarification=True)
        log_event(trace_id, "clarification", {"confidence": confidence, "question": clarification_msg})
        return _make_result(
            answer=clarification_msg,
            status="clarification",
            plan=plan,
            verification={"status": "skipped", "warnings": ["Clarification required"]},
            clarification=clarification_msg,
        )

    stage_started = time.perf_counter()
    allowed, rejection_reason = guard(normalized_query, plan, trace_id)
    _record_stage_latency("guard", stage_started)
    if not allowed:
        return _make_result(
            answer=rejection_reason or REJECTION_RESPONSE,
            status="rejected",
            plan=plan,
        )

    # Validate plan for deterministic execution
    stage_started = time.perf_counter()
    is_valid, validation_msg = validate_plan_for_execution(
        normalized_query,
        plan,
        trace_id,
        allow_model_fallback=reasoning_model is not None,
    )
    _record_stage_latency("validator", stage_started)
    if not is_valid:
        update_context(conversation_id, plan, trace_id, pending_clarification=True)
        log_event(trace_id, "clarification", {"question": validation_msg})
        return _make_result(
            answer=validation_msg,
            status="clarification",
            plan=plan,
            verification={"status": "skipped", "warnings": ["Clarification required"]},
            clarification=validation_msg,
        )

    if _pipeline_timed_out():
        reason = "Request timed out while processing. Please narrow the query and try again."
        log_event(
            trace_id,
            "pipeline_timeout",
            {"elapsed_ms": _elapsed_pipeline_ms(), "timeout_ms": pipeline_timeout_ms},
        )
        return _make_result(
            answer=reason,
            status="error",
            plan=plan,
            verification={"status": "failed", "warnings": [reason]},
        )

    # Deterministic SQL generation
    try:
        stage_started = time.perf_counter()
        generated_sql = generate_sql(
            plan,
            normalized_query,
            reasoning_model,
            trace_id,
            llm_timeout_seconds=max(0.1, min(llm_timeout_seconds, _remaining_pipeline_ms() / 1000)),
        )
        _record_stage_latency("query_agent", stage_started)
    except ValueError as e:
        clarification = str(e)
        update_context(conversation_id, plan, trace_id, pending_clarification=True)
        log_event(trace_id, "clarification", {"question": clarification})
        return _make_result(
            answer=clarification,
            status="clarification",
            plan=plan,
            verification={"status": "skipped", "warnings": ["Clarification required"]},
            clarification=clarification,
        )
    except Exception as e:
        log_event(trace_id, "query_agent_error", {"error": str(e)})
        return _make_result(
            answer=_friendly_llm_error(e),
            status="error",
            plan=plan,
            verification={"status": "failed", "warnings": ["Query generation failed"]},
        )

    # Execute through deterministic executor boundary
    if _pipeline_timed_out():
        reason = "Request timed out while processing. Please narrow the query and try again."
        log_event(
            trace_id,
            "pipeline_timeout",
            {"elapsed_ms": _elapsed_pipeline_ms(), "timeout_ms": pipeline_timeout_ms},
        )
        return _make_result(
            answer=reason,
            status="error",
            plan=plan,
            verification={"status": "failed", "warnings": [reason]},
        )

    stage_started = time.perf_counter()
    execution_out = execute_sql(generated_sql, trace_id, semantic_cache_key=query_fingerprint)
    _record_stage_latency("execution", stage_started)
    if not execution_out.get("ok"):
        exec_status = execution_out.get("status") or "error"
        reason = execution_out.get("reason") or "Execution failed"
        warning_label = "SQL blocked" if exec_status == "blocked" else "Execution failed"
        return _make_result(
            answer=reason,
            status=exec_status,
            plan=plan,
            sql=execution_out.get("sql") or generated_sql,
            verification={"status": "failed", "warnings": [warning_label]},
        )

    generated_sql = str(execution_out.get("sql") or generated_sql)
    results = execution_out.get("results") or []

    stage_started = time.perf_counter()
    verification = verify(plan, results, trace_id)
    _record_stage_latency("verification", stage_started)
    if budget_warnings:
        existing_warnings = verification.get("warnings") or []
        verification["warnings"] = [*existing_warnings, *budget_warnings]
        if verification.get("status") == "ok":
            verification["status"] = "warning"

    model = reasoning_model

    if _pipeline_timed_out():
        reason = "Request timed out while processing. Please narrow the query and try again."
        log_event(
            trace_id,
            "pipeline_timeout",
            {"elapsed_ms": _elapsed_pipeline_ms(), "timeout_ms": pipeline_timeout_ms},
        )
        return _make_result(
            answer=reason,
            status="error",
            plan=plan,
            verification={"status": "failed", "warnings": [reason]},
        )

    stage_started = time.perf_counter()
    answer, referenced_nodes = synthesize(
        plan,
        normalized_query,
        generated_sql,
        results,
        model,
        trace_id,
        llm_timeout_seconds=max(0.1, min(llm_timeout_seconds, _remaining_pipeline_ms() / 1000)),
    )
    _record_stage_latency("response", stage_started)

    update_context(conversation_id, plan, trace_id)

    return _make_result(
        answer=answer,
        status="success",
        plan=plan,
        sql=generated_sql,
        results=results[:20],
        referenced_nodes=referenced_nodes,
        verification=verification,
        row_count=len(results),
    )
