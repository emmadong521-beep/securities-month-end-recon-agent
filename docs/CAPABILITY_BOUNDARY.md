# Capability Boundary

## Positioning

This project focuses on securities month-end reconciliation, evidence-chain tracing, exception severity grading, similar case matching, and root-cause reporting.

## Capability Comparison

| Dimension | Traditional finance systems | BI / dashboards | LLM-only tools | This PoC |
|---|---|---|---|---|
| Data processing | Structured workflows and configured rules | Visualizes prepared data | No reliable data processing by itself | Synthetic month-end chain with deterministic checks |
| Exception detection | Rule-based checks | Usually requires precomputed flags | May hallucinate if not grounded | Deterministic reconciliation and allocation checks |
| Root-cause analysis | Users inspect tables and logs | Drilldown depends on prepared model | Can explain text but lacks traceability | Evidence-chain tracing plus case matching |
| Financial calculation | Deterministic | Deterministic if modeled | Not reliable for calculation | Always local deterministic code |
| Interaction | Menu-driven | Filter and chart driven | Natural language | Natural language task plus visible tool trace |
| Auditability | High in production systems | Medium to high | Low if ungrounded | Traceable to synthetic data tables and tools |

## Current Limitations

- Local PoC only.
- Synthetic detailed data.
- No production finance-system integration.
- Case matching is deterministic scoring, not a full vector RAG system.
- LLM enhances task understanding and explanation only.
