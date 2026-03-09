"""Commodity Linkage Engine.

Maps commodity price movements (CPO, coal, nickel, crude oil) to
Indonesian equity earnings impact estimates.  Integrates climate
signals (ENSO, rainfall, fire hotspots) with production forecasts
and publishes actionable alerts via Kafka.

Subpackages:

* ``commodity_sensitivity_models`` -- Per-commodity sensitivity models
  for plantation, mining, and energy equities.
* ``climate_commodity_correlation`` -- ENSO, rainfall, and fire-hotspot
  models that feed into commodity production forecasts.
"""

__version__ = "0.1.0"
