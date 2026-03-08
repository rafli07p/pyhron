# ADR-005: Python-First with Zero-Rewrite Rust Migration Path

## Status
Accepted

## Context
The team has deep Python expertise. Performance-critical paths (risk checks, order matching) may eventually need Rust-level latency. We need an architecture that allows incremental Rust migration without rewriting the entire system.

## Decision
Build everything in Python first. Design all service boundaries around Kafka topics and protobuf contracts. Risk checks are pure functions. The OMS state machine has no hidden side effects. When Rust replaces a service, it consumes the same Kafka topic and produces the same protobuf output — zero changes to adjacent services.

## Consequences
- **Positive:** Ship fast in Python. Each service is independently replaceable. Risk checks can be ported to Rust one function at a time. Protobuf contracts are the stable seam — not Python classes.
- **Negative:** Python performance ceiling for ultra-low-latency use cases. Discipline required to keep side effects out of pure functions.
- **Mitigation:** Pure function design enforced in code review. `frozen=True` dataclasses for risk check results. Kafka interface is the contract, not the implementation language.
