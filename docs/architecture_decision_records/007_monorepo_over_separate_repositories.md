# ADR-007: Monorepo over Separate Repositories

## Status
Accepted

## Context
The Pyhron platform consists of multiple services (API gateway, risk engine, data ingestion workers, strategy execution, backtesting), shared libraries (protobuf contracts, database models, common utilities), and infrastructure configuration (Terraform, Kubernetes manifests, Docker files). We needed to decide whether to organize these as separate repositories or a single monorepo.

Key considerations:
- Protobuf contracts in `proto/` are consumed by every service. Changes to message schemas must be atomically visible to all producers and consumers.
- Database migrations in `alembic/` affect multiple services that read from the same TimescaleDB schemas (market_data, trading, risk, macro, commodity, alternative_data, fixed_income, governance, audit, analytics).
- The team is small (fewer than 10 engineers) and moves fast on cross-cutting changes.
- Deployment cadence is high — multiple deploys per day during active development.

## Decision
Use a monorepo structure where all services, shared libraries, proto definitions, infrastructure code, and documentation live in a single Git repository.

### Repository layout
```
pyhron/
├── apps/                    # Application entry points (API, workers)
├── services/                # Domain service modules
├── shared/                  # Shared libraries and proto_generated
├── proto/                   # Protobuf contract definitions
├── infra/                   # Docker, Kubernetes, Terraform
├── scripts/                 # Dev and ops scripts
├── tests/                   # Test suites
├── docs/                    # Documentation and ADRs
├── pyproject.toml           # Single Poetry project
└── docker-compose.yaml      # Local development stack
```

### Rationale
1. **Shared proto contracts.** Protobuf definitions in `proto/` are the canonical API between services. A monorepo guarantees that generated Python bindings in `shared/proto_generated/` are always in sync with the `.proto` source. In a multi-repo setup, we would need a separate proto registry and versioning scheme, adding complexity without proportional benefit at our current scale.

2. **Atomic deployments.** When a database migration adds a column that a new API endpoint reads and a Kafka consumer writes, all three changes land in a single PR. Reviewers see the full picture, CI validates compatibility, and rollback is a single revert. Cross-repo coordination for such changes is error-prone.

3. **Consistent tooling.** A single `pyproject.toml` with Poetry manages all Python dependencies. One `ruff.toml` enforces formatting and linting rules. One `.github/workflows/ci.yaml` runs all checks. Developers do not need to context-switch between different repo conventions.

4. **Simplified onboarding.** New engineers clone one repo, run `docker compose up -d && poetry install`, and have the entire platform running locally. No need to discover and clone five separate repos.

5. **Refactoring velocity.** Moving code between `services/` and `shared/`, renaming protobuf fields, or restructuring modules is a single commit with full IDE support for cross-references.

## Consequences

### Positive
- Single source of truth for all proto contracts, database schemas, and infrastructure definitions.
- CI validates the entire dependency graph on every PR — no broken cross-service interfaces reach production.
- `git log` and `git blame` provide full context across service boundaries.
- Simplified dependency management — one lockfile, one virtual environment.

### Negative
- CI build times grow as the codebase grows. Mitigation: path-based job triggers (`paths:` filter in GitHub Actions), caching, and parallelism.
- Git clone size increases over time. Mitigation: shallow clones in CI (`fetch-depth: 1`), Git LFS for large artifacts if needed.
- Risk of tight coupling between services if module boundaries are not enforced. Mitigation: clear schema separation (10 PostgreSQL schemas), domain-driven directory structure, and code review discipline.
- All engineers see all code, which may not scale past ~20 engineers. Mitigation: revisit if team size exceeds this threshold; consider code ownership via `CODEOWNERS` file.

### Migration path
If the monorepo becomes a bottleneck (CI times >15 minutes, team >20 engineers), we can extract services into separate repos while keeping `proto/` as a shared submodule or publishing generated bindings as a private PyPI package. The current directory structure makes this extraction straightforward.
