from __future__ import annotations

import socket
import time
import hashlib
import json
import uuid
from typing import Any

import google.generativeai as genai
import httpx

from .guard_agent import guard
from .intent_schema import validate_and_normalize_plan
from .memory import get_context, update_context
from .observability import build_agent_trace_summary, log_event
from .planner_agent import plan as planner_plan
from .query_agent import generate_sql
from .response_agent import synthesize
from .executor_agent import execute_sql
from .validator_agent import validate_plan_for_execution
from .verifier_agent import verify
from .runtime_config import RuntimeConfig, get_runtime_config

try:
    from ..guardrails import REJECTION_RESPONSE, normalize_user_query
except ImportError:
    from guardrails import REJECTION_RESPONSE, normalize_user_query


GEMINI_HOST = "generativelanguage.googleapis.com"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


class _ModelResponse:
    def __init__(self, text: str) -> None:
        self.text = text


class _GroqModel:
    provider = "groq"

    def __init__(self, api_key: str, model_name: str) -> None:
        self.api_key = api_key
        self.model_name = model_name

    def _to_messages(self, prompt: Any) -> list[dict[str, str]]:
        if isinstance(prompt, str):
            return [{"role": "user", "content": prompt}]

        if isinstance(prompt, list):
            out: list[dict[str, str]] = []
            for item in prompt:
                if not isinstance(item, dict):
                    continue
                role = item.get("role", "user")
                if role == "model":
                    role = "assistant"
                parts = item.get("parts")
                if isinstance(parts, list):
                    chunks: list[str] = []
                    for part in parts:
                        if isinstance(part, dict) and "text" in part:
                            chunks.append(str(part.get("text", "")))
                        elif isinstance(part, str):
                            chunks.append(part)
                    content = "\n".join(c for c in chunks if c).strip()
                else:
                    content = str(item.get("content", "")).strip()
                if content:
                    out.append({"role": role, "content": content})
            if out:
                return out

        return [{"role": "user", "content": str(prompt)}]

    def generate_content(self, prompt: Any, request_options: dict[str, Any] | None = None) -> _ModelResponse:
        timeout = (request_options or {}).get("timeout", get_runtime_config().llm_timeout_seconds)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model_name,
            "messages": self._to_messages(prompt),
            "temperature": 0,
        }
        response = httpx.post(GROQ_API_URL, headers=headers, json=payload, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        text = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        return _ModelResponse(text or "")


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

    def _pipeline_timeout_result(intent_plan: dict[str, Any] | None) -> dict[str, Any]:
        reason = "Request timed out while processing. Please narrow the query and try again."
        verification = {"status": "failed", "warnings": [reason]}
        log_event(
            trace_id,
            "pipeline_timeout",
            {"elapsed_ms": _elapsed_pipeline_ms(), "timeout_ms": pipeline_timeout_ms},
        )
        return {
            "answer": reason,
            "query": None,
            "results": None,
            "result_columns": None,
            "total_results": None,
            "referenced_nodes": [],
            "status": "error",
            "trace_id": trace_id,
            "conversation_id": conversation_id,
            "intent": intent_plan.get("intent") if intent_plan else None,
            "plan": intent_plan,
            "verification": verification,
            "agent_trace": _agent_trace(intent_plan, None, verification, None, None),
        }

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

    log_event(trace_id, "request", {"query": normalized_query, "conversation_id": conversation_id})

    def _query_fingerprint(query: str, plan_payload: dict[str, Any] | None = None) -> str:
        base = {
            "query": query,
            "plan": plan_payload or {},
        }
        raw = json.dumps(base, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]

    if not normalized_query:
        return {
            "answer": "Query cannot be empty.",
            "query": None,
            "results": None,
            "result_columns": None,
            "total_results": None,
            "referenced_nodes": [],
            "status": "rejected",
            "trace_id": trace_id,
            "conversation_id": conversation_id,
            "intent": None,
            "plan": None,
            "verification": {"status": "skipped", "warnings": ["Empty query"]},
            "agent_trace": _agent_trace(None, None, {"status": "skipped", "warnings": ["Empty query"]}, None, None),
        }

    if len(normalized_query) > 2000:
        return {
            "answer": "Query is too long. Please keep it under 2000 characters.",
            "query": None,
            "results": None,
            "result_columns": None,
            "total_results": None,
            "referenced_nodes": [],
            "status": "rejected",
            "trace_id": trace_id,
            "conversation_id": conversation_id,
            "intent": None,
            "plan": None,
            "verification": {"status": "skipped", "warnings": ["Query too long"]},
            "agent_trace": _agent_trace(None, None, {"status": "skipped", "warnings": ["Query too long"]}, None, None),
        }

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
        return {
            "answer": clarification_msg,
            "query": None,
            "results": None,
            "result_columns": None,
            "total_results": None,
            "referenced_nodes": [],
            "status": "clarification",
            "trace_id": trace_id,
            "conversation_id": conversation_id,
            "intent": None,
            "plan": None,
            "verification": {"status": "skipped", "warnings": ["Clarification required"]},
            "agent_trace": _agent_trace(None, None, {"status": "skipped", "warnings": ["Clarification required"]}, clarification_msg, None),
        }

    if _pipeline_timed_out():
        return _pipeline_timeout_result(plan)

    clarification_msg = plan.get("clarification")
    confidence = float(plan.get("confidence", 1.0))
    query_fingerprint = _query_fingerprint(normalized_query, plan)
    log_event(trace_id, "query_fingerprint", {"fingerprint": query_fingerprint})
    if clarification_msg and confidence < 0.7:
        update_context(conversation_id, plan, trace_id, pending_clarification=True)
        log_event(trace_id, "clarification", {"confidence": confidence, "question": clarification_msg})
        return {
            "answer": clarification_msg,
            "query": None,
            "results": None,
            "result_columns": None,
            "total_results": None,
            "referenced_nodes": [],
            "status": "clarification",
            "trace_id": trace_id,
            "conversation_id": conversation_id,
            "intent": plan.get("intent"),
            "plan": plan,
            "verification": {"status": "skipped", "warnings": ["Clarification required"]},
            "agent_trace": _agent_trace(plan, None, {"status": "skipped", "warnings": ["Clarification required"]}, clarification_msg, None),
        }

    stage_started = time.perf_counter()
    allowed, rejection_reason = guard(normalized_query, plan, trace_id)
    _record_stage_latency("guard", stage_started)
    if not allowed:
        return {
            "answer": rejection_reason or REJECTION_RESPONSE,
            "query": None,
            "results": None,
            "result_columns": None,
            "total_results": None,
            "referenced_nodes": [],
            "status": "rejected",
            "trace_id": trace_id,
            "conversation_id": conversation_id,
            "intent": plan.get("intent"),
            "plan": plan,
            "verification": {"status": "skipped", "warnings": []},
            "agent_trace": _agent_trace(plan, None, {"status": "skipped", "warnings": []}, None, None),
        }

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
        return {
            "answer": validation_msg,
            "query": None,
            "results": None,
            "result_columns": None,
            "total_results": None,
            "referenced_nodes": [],
            "status": "clarification",
            "trace_id": trace_id,
            "conversation_id": conversation_id,
            "intent": plan.get("intent"),
            "plan": plan,
            "verification": {"status": "skipped", "warnings": ["Clarification required"]},
            "agent_trace": _agent_trace(plan, None, {"status": "skipped", "warnings": ["Clarification required"]}, validation_msg, None),
        }

    if _pipeline_timed_out():
        return _pipeline_timeout_result(plan)

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
        return {
            "answer": clarification,
            "query": None,
            "results": None,
            "result_columns": None,
            "total_results": None,
            "referenced_nodes": [],
            "status": "clarification",
            "trace_id": trace_id,
            "conversation_id": conversation_id,
            "intent": plan.get("intent"),
            "plan": plan,
            "verification": {"status": "skipped", "warnings": ["Clarification required"]},
            "agent_trace": _agent_trace(plan, None, {"status": "skipped", "warnings": ["Clarification required"]}, clarification, None),
        }
    except Exception as e:
        log_event(trace_id, "query_agent_error", {"error": str(e)})
        return {
            "answer": f"Failed to generate query: {str(e)}",
            "query": None,
            "results": None,
            "result_columns": None,
            "total_results": None,
            "referenced_nodes": [],
            "status": "error",
            "trace_id": trace_id,
            "conversation_id": conversation_id,
            "intent": plan.get("intent"),
            "plan": plan,
            "verification": {"status": "failed", "warnings": ["Query generation failed"]},
            "agent_trace": _agent_trace(plan, None, {"status": "failed", "warnings": ["Query generation failed"]}, None, None),
        }

    # Execute through deterministic executor boundary
    if _pipeline_timed_out():
        return _pipeline_timeout_result(plan)

    stage_started = time.perf_counter()
    execution_out = execute_sql(generated_sql, trace_id, semantic_cache_key=query_fingerprint)
    _record_stage_latency("execution", stage_started)
    if not execution_out.get("ok"):
        status = execution_out.get("status") or "error"
        reason = execution_out.get("reason") or "Execution failed"
        warning_label = "SQL blocked" if status == "blocked" else "Execution failed"
        return {
            "answer": reason,
            "query": execution_out.get("sql") or generated_sql,
            "results": None,
            "result_columns": None,
            "total_results": None,
            "referenced_nodes": [],
            "status": status,
            "trace_id": trace_id,
            "conversation_id": conversation_id,
            "intent": plan.get("intent"),
            "plan": plan,
            "verification": {"status": "failed", "warnings": [warning_label]},
            "agent_trace": _agent_trace(plan, execution_out.get("sql") or generated_sql, {"status": "failed", "warnings": [warning_label]}, None, None),
        }

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
        return _pipeline_timeout_result(plan)

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

    return {
        "answer": answer,
        "query": generated_sql,
        "results": results[:20],
        "result_columns": list(results[0].keys()) if results else [],
        "total_results": len(results),
        "referenced_nodes": referenced_nodes,
        "status": "success",
        "trace_id": trace_id,
        "conversation_id": conversation_id,
        "intent": plan.get("intent"),
        "plan": plan,
        "verification": verification,
        "agent_trace": _agent_trace(plan, generated_sql, verification, None, len(results)),
    }
