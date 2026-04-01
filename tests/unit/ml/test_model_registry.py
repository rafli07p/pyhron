"""Tests for ML model registry."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from pyhron.ml.model_registry import ModelRegistry, PyhronMLError


class TestModelRegistry:
    def test_pit_safe_loading_raises_for_future_model(self) -> None:
        """Loading a model with as_of before registration should raise."""
        registry = ModelRegistry(mlflow_client=MagicMock())

        mock_mlflow = MagicMock()
        mock_experiment = MagicMock()
        mock_experiment.experiment_id = "exp-1"
        mock_mlflow.get_experiment_by_name.return_value = mock_experiment
        mock_mlflow.search_runs.return_value = pd.DataFrame()

        as_of = datetime(2020, 1, 1, tzinfo=UTC)
        with patch.dict("sys.modules", {"mlflow": mock_mlflow}), pytest.raises(PyhronMLError, match="No model"):
            registry.load_as_of("test_model", as_of)

    def test_register_model_returns_run_id(self) -> None:
        registry = ModelRegistry(mlflow_client=MagicMock())

        mock_mlflow = MagicMock()
        mock_run = MagicMock()
        mock_run.info.run_id = "abc123-def456"
        mock_mlflow.start_run.return_value.__enter__ = MagicMock(return_value=mock_run)
        mock_mlflow.start_run.return_value.__exit__ = MagicMock(return_value=False)

        with patch.dict("sys.modules", {"mlflow": mock_mlflow, "mlflow.sklearn": MagicMock()}):
            run_id = registry.register_model(
                name="test_model",
                model=MagicMock(),
                metrics={"sharpe": 1.5},
                feature_names=["momentum_5d", "rsi_14"],
                as_of=datetime(2024, 1, 1, tzinfo=UTC),
            )
            assert run_id == "abc123-def456"

    def test_no_experiment_raises(self) -> None:
        registry = ModelRegistry(mlflow_client=MagicMock())

        mock_mlflow = MagicMock()
        mock_mlflow.get_experiment_by_name.return_value = None

        with (
            patch.dict("sys.modules", {"mlflow": mock_mlflow}),
            pytest.raises(PyhronMLError, match="No experiment found"),
        ):
            registry.load_latest("nonexistent")

    def test_compare_runs_empty(self) -> None:
        registry = ModelRegistry(mlflow_client=MagicMock())

        mock_mlflow = MagicMock()
        mock_mlflow.get_experiment_by_name.return_value = None

        with patch.dict("sys.modules", {"mlflow": mock_mlflow}):
            result = registry.compare_runs("nonexistent")
            assert result.empty
