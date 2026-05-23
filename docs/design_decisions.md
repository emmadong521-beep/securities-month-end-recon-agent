# Design Decisions

## Scope

This project is a securities finance AI PoC focused on month-end reconciliation.
It intentionally stays lightweight:

- pandas and DuckDB handle deterministic data processing.
- Streamlit provides the demo UI.
- The Agent layer orchestrates existing tools instead of replacing accounting
  logic with model output.

## Key Decisions

### Use synthetic detailed data

Public audit-report figures can calibrate aggregate scale, but customer, trade,
voucher, branch, and allocation details must remain synthetic.

### Keep DuckDB local

A local analytical database is enough for reproducible PoC workflows and avoids
external service dependencies.

### Keep rules deterministic

Reconciliation, exception severity, evidence chain, and data export must be
reproducible and testable.

### Make LLM optional

The Volcengine Ark integration enhances language understanding and expression
only. If configuration is missing or API calls fail, the app falls back to Mock
Agent mode.

### Preserve tool-call trace

Agent output is useful only if users can see the plan, tool inputs, observations,
evidence chain, and final conclusion.

### Export validated outputs

`validated_actual_revenue.csv`, `validated_allocated_expense.csv`, and
`validation_summary.csv` demonstrate how checked month-end data can feed
downstream management analysis.

## Non-Goals

- No production data ingestion.
- No claim that synthetic exception patterns represent all real-world
  reconciliation cases.
- No automated accounting posting or write-back to external finance systems.
- No model-generated amount calculation.

## Quality Boundaries

Tests cover schema, seed data, reconciliation rules, evidence chains, severity
grading, historical case matching, Agent behavior, LLM fallback, data quality
reporting, and validated export generation.

Coverage is reported with `pytest-cov`; low-coverage modules are documented
rather than hidden.
