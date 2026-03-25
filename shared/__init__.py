"""Pyhron shared library.

Core package providing schemas, contracts, utilities, configuration,
and security primitives shared across all Pyhron platform services.

Subpackages:

* ``shared.schemas`` -- Pydantic domain event models (market, order,
  portfolio, research).
* ``shared.contracts`` -- API response envelopes and message type
  enumerations.
* ``shared.utils`` -- Retry, rate limiting, JSON serialization, ID
  generation, and timestamp helpers.
* ``shared.configuration_settings`` -- Centralised application settings
  via Pydantic BaseSettings.
* ``shared.security`` -- JWT authentication, RBAC, and audit logging.
"""

__version__ = "0.1.0"
