# Capability Boundary

## Positioning

This project focuses on securities month-end reconciliation, evidence-chain tracing, exception severity grading, similar case matching, and root-cause reporting.

It is designed as a local finance AI PoC. The core financial calculations are deterministic and traceable, while the Agent layer helps organize the investigation path, evidence, and final explanation.

## Capability Comparison

| Dimension | Traditional finance systems | BI / dashboards | LLM-only tools | This PoC |
|---|---|---|---|---|
| Data processing | Structured workflows and configured rules | Visualizes prepared data | No reliable data processing by itself | Synthetic month-end chain with deterministic checks |
| Exception detection | Rule-based checks | Usually requires precomputed flags | May hallucinate if not grounded | Deterministic reconciliation and allocation checks |
| Root-cause analysis | Users inspect tables and logs | Drilldown depends on prepared model | Can explain text but lacks traceability | Evidence-chain tracing plus similar case matching |
| Financial calculation | Deterministic | Deterministic if modeled | Not reliable for calculation | Always local deterministic code |
| Interaction | Menu-driven | Filter and chart driven | Natural language | Natural language task plus visible tool trace |
| Auditability | High in production systems | Medium to high | Low if ungrounded | Traceable to synthetic data tables, rules, and tool outputs |

## What This PoC Does

This project demonstrates how an Agent-style workflow can support finance users during month-end close.

The workflow covers:

1. Detect reconciliation exceptions.
2. Classify exception severity.
3. Build an evidence chain across source data, subledger, GL, and allocation results.
4. Match similar historical root-cause cases.
5. Generate a structured root-cause report.
6. Support follow-up questions based on the evidence chain.

## What This PoC Does Not Do

This project does not attempt to replace a production finance system.

It does not:

- connect to a real broker core system;
- post or reverse real accounting vouchers;
- process real customer, trade, or voucher data;
- perform regulatory reporting;
- use LLM output as the source of truth for financial numbers.

## Deterministic Calculation Boundary

Financial calculations are handled by local code.

This includes:

- commission reconciliation;
- revenue-subledger-to-GL comparison;
- allocation-ratio validation;
- severity grading;
- amount difference calculation;
- validated revenue and allocated expense export.

The LLM is used only for language-oriented tasks such as task interpretation, answer wording, and follow-up response generation.

## Data Boundary

The project uses synthetic detailed data.

Public audit-report figures may be used only for aggregate-scale calibration. Detailed trade, customer, voucher, branch, cost pool, and allocation data is generated for demonstration and testing.

The data does not represent any real company’s internal operating records.

## Current Limitations

- Local PoC only.
- Synthetic detailed data.
- No production finance-system integration.
- Similar case matching is deterministic scoring, not a full vector RAG system.
- LLM enhances task understanding and explanation only.
- The workflow focuses on selected reconciliation scenarios rather than the full month-end close process.
- The project exposes tool-call and analysis traces, not raw model reasoning.
