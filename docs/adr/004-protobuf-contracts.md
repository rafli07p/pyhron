# ADR-004: Protobuf as Inter-Service Contract Format

## Status
Accepted

## Context
Pyhron is designed for eventual migration of performance-critical paths from Python to Rust. Inter-service communication must use a format that both languages can generate code for, with strong schema evolution guarantees.

## Decision
Use Protocol Buffers (proto3) for all Kafka message schemas. Proto files live in `/proto/` and generate Python bindings via `scripts/generate_proto.sh`. Rust bindings will use `prost` when the migration begins.

## Consequences
- **Positive:** Language-agnostic serialization. Schema evolution via field numbering. Compact binary format reduces Kafka storage. Generated code ensures type safety. Same `.proto` files compile to both Python and Rust.
- **Negative:** Proto compilation step in CI. Less human-readable than JSON on the wire. Proto-to-ORM mapping requires explicit conversion layer.
- **Mitigation:** CI job compiles protos and checks generated files are committed. JSON transcoding available for debugging. Explicit `_signal_to_order()` and `_build_event()` mapping methods.
