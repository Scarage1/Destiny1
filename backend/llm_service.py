"""
LLM service: NL→SQL generation and grounded answer synthesis using Google Gemini.
"""

import os
import json
import re
import uuid
from typing import Any

import google.generativeai as genai

from database import get_schema_description, execute_readonly_query
from guardrails import (
    check_domain_relevance,
    validate_sql_safety,
    sanitize_sql,
    REJECTION_RESPONSE,
)

# Configure Gemini
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")


def _get_model():
    """Get configured Gemini model."""
    genai.configure(api_key=GEMINI_API_KEY)
    return genai.GenerativeModel("gemini-2.0-flash")


# System prompt for NL→SQL generation
SQL_GENERATION_PROMPT = """You are a SQL query generator for an SAP Order-to-Cash (O2C) dataset stored in SQLite.

DATABASE SCHEMA:
{schema}

IMPORTANT RELATIONSHIPS:
- sales_order_headers.soldToParty links to business_partners.businessPartner (Customer)
- sales_order_items.salesOrder links to sales_order_headers.salesOrder
- sales_order_items.material links to products.product
- sales_order_items.productionPlant links to plants.plant
- outbound_delivery_items.referenceSdDocument links to sales_order_headers.salesOrder (Sales Order → Delivery)
- outbound_delivery_items.deliveryDocument links to outbound_delivery_headers.deliveryDocument
- billing_document_items.referenceSdDocument links to outbound_delivery_headers.deliveryDocument (Delivery → Billing)
- billing_document_items.material links to products.product
- billing_document_headers.accountingDocument links to journal_entry_items.accountingDocument (Billing → Journal Entry)
- billing_document_headers.soldToParty links to business_partners.businessPartner
- journal_entry_items.clearingAccountingDocument links to payments.accountingDocument (Journal → Payment)
- journal_entry_items.referenceDocument can link to billing_document_headers.billingDocument

FLOW: SalesOrder → Delivery → BillingDocument → JournalEntry → Payment

RULES:
1. Generate ONLY a single SELECT query (no writes, no DDL).
2. Use SQLite-compatible syntax ONLY.
3. Always include a LIMIT clause (max 100 rows).
4. Use JOINs to traverse relationships when needed.
5. For "broken flow" queries: a sales order has a broken flow if it has deliveries but no billing, or billing without delivery.
6. When asked about products and billing documents, join billing_document_items with products via the material field.
7. Product names are in the product_descriptions table (join on product field, filter language='EN').

Return ONLY a valid SQL query. No explanation, no markdown code blocks, just the raw SQL."""

# System prompt for answer synthesis
ANSWER_SYNTHESIS_PROMPT = """You are a data analyst answering questions about an SAP Order-to-Cash dataset.

You are given:
1. The user's original question
2. The SQL query that was executed
3. The query results

RULES:
1. Answer ONLY based on the provided query results. Do not make up or infer data not present in the results.
2. If the results are empty, say "No matching records found in the dataset."
3. Be concise but thorough. Use specific numbers and IDs from the results.
4. Format your answer clearly with bullet points or tables when appropriate.
5. If results contain entity IDs, mention them so they can be highlighted in the graph.
6. Do NOT add disclaimers about being an AI or data limitations unless the results are empty.

Provide a clear, data-grounded answer."""


def process_query(user_query: str) -> dict[str, Any]:
    """
    Full query pipeline: guardrails → NL→SQL → execute → synthesize answer.
    Returns structured response with answer, query, results, and referenced entities.
    """
    trace_id = str(uuid.uuid4())

    # Step 1: Domain guardrail
    is_relevant, rejection_reason = check_domain_relevance(user_query)
    if not is_relevant:
        return {
            "answer": rejection_reason or REJECTION_RESPONSE,
            "query": None,
            "results": None,
            "result_columns": None,
            "total_results": None,
            "referenced_nodes": [],
            "status": "rejected",
            "trace_id": trace_id,
        }

    # Step 2: Generate SQL
    try:
        schema = get_schema_description()
        model = _get_model()

        sql_prompt = SQL_GENERATION_PROMPT.format(schema=schema)
        response = model.generate_content(
            [
                {"role": "user", "parts": [{"text": sql_prompt}]},
                {
                    "role": "model",
                    "parts": [
                        {
                            "text": "I understand. I will generate SQLite SELECT queries for the O2C dataset. Send your question."
                        }
                    ],
                },
                {"role": "user", "parts": [{"text": user_query}]},
            ]
        )

        generated_sql = response.text.strip()

        # Clean markdown code blocks if present
        generated_sql = re.sub(r"^```(?:sql)?\s*", "", generated_sql).strip()
        generated_sql = re.sub(r"\s*```$", "", generated_sql).strip()

    except Exception as e:
        return {
            "answer": f"Failed to generate query: {str(e)}",
            "query": None,
            "results": None,
            "result_columns": None,
            "total_results": None,
            "referenced_nodes": [],
            "status": "error",
            "trace_id": trace_id,
        }

    # Step 3: Safety validation
    is_safe, safety_error = validate_sql_safety(generated_sql)
    if not is_safe:
        return {
            "answer": f"Generated query was blocked by safety checks: {safety_error}",
            "query": generated_sql,
            "results": None,
            "result_columns": None,
            "total_results": None,
            "referenced_nodes": [],
            "status": "blocked",
            "trace_id": trace_id,
        }

    # Sanitize
    generated_sql = sanitize_sql(generated_sql)

    # Step 4: Execute query
    try:
        results = execute_readonly_query(generated_sql)
    except Exception as e:
        error_msg = str(e)
        # Retry once with error context
        try:
            retry_prompt = f"""The previous SQL query failed with error: {error_msg}
Original query: {generated_sql}
Original question: {user_query}

Please generate a CORRECTED SQL query. Fix the error and return ONLY the SQL."""
            response = model.generate_content(retry_prompt)
            generated_sql = response.text.strip()
            generated_sql = re.sub(
                r"^```(?:sql)?\s*", "", generated_sql
            ).strip()
            generated_sql = re.sub(r"\s*```$", "", generated_sql).strip()
            generated_sql = sanitize_sql(generated_sql)

            is_safe, safety_error = validate_sql_safety(generated_sql)
            if not is_safe:
                return {
                    "answer": f"Retry query blocked: {safety_error}",
                    "query": generated_sql,
                    "results": None,
                    "result_columns": None,
                    "total_results": None,
                    "referenced_nodes": [],
                    "status": "blocked",
                    "trace_id": trace_id,
                }

            results = execute_readonly_query(generated_sql)
        except Exception as retry_error:
            return {
                "answer": f"Query execution failed after retry: {str(retry_error)}",
                "query": generated_sql,
                "results": None,
                "result_columns": None,
                "total_results": None,
                "referenced_nodes": [],
                "status": "error",
                "trace_id": trace_id,
            }

    # Step 5: Extract referenced entity IDs for graph highlighting
    referenced_nodes = _extract_referenced_nodes(results)

    # Step 6: Synthesize grounded answer
    if len(results) == 0:
        answer = "No matching records found in the dataset."
    else:
        try:
            # Limit results for answer synthesis to avoid token overflow
            results_for_synthesis = (
                results[:50] if len(results) > 50 else results
            )
            results_text = json.dumps(
                results_for_synthesis, indent=2, default=str
            )

            answer_prompt = f"""{ANSWER_SYNTHESIS_PROMPT}

Question: {user_query}
SQL Query: {generated_sql}
Results ({len(results)} rows):
{results_text}"""

            response = model.generate_content(answer_prompt)
            answer = response.text.strip()

        except Exception:
            # Fallback: raw results summary
            answer = f"Query returned {len(results)} results. Here are the first few:\n\n"
            for row in results[:5]:
                answer += f"- {json.dumps(row, default=str)}\n"

    return {
        "answer": answer,
        "query": generated_sql,
        "results": results[:20],  # Cap results sent to frontend
        "result_columns": list(results[0].keys()) if results else [],
        "total_results": len(results),
        "referenced_nodes": referenced_nodes,
        "status": "success",
        "trace_id": trace_id,
    }


def _extract_referenced_nodes(results: list[dict]) -> list[str]:
    """Extract graph node IDs from query results for highlighting."""
    node_ids = set()

    # Map common column names to node type prefixes
    column_to_type = {
        "salesOrder": "SalesOrder",
        "deliveryDocument": "Delivery",
        "billingDocument": "BillingDocument",
        "accountingDocument": "JournalEntry",
        "businessPartner": "Customer",
        "soldToParty": "Customer",
        "customer": "Customer",
        "product": "Product",
        "material": "Product",
        "plant": "Plant",
        "productionPlant": "Plant",
    }

    for row in results:
        for col, node_type in column_to_type.items():
            if col in row and row[col]:
                node_ids.add(f"{node_type}:{row[col]}")

    return list(node_ids)
