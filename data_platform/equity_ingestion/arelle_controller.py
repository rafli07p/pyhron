"""Arelle XBRL controller singleton and Celery lifecycle hooks.

Owns a single `arelle.Cntlr.Cntlr` instance per process. Each Celery
worker fork pays the 2-5s DTS cache warm-up once at `worker_process_init`;
tasks reuse the singleton with no per-task initialization cost.

Thread safety
-------------
`Cntlr` is NOT thread-safe. It maintains mutable caches for loaded DTS,
taxonomy schema, and model graph state. Running Celery with
`--pool=gevent` or `--pool=threads` will produce non-deterministic parse
results under concurrent load.

Required Celery pool: `prefork` (default on POSIX). Validate at worker
boot by calling `register_celery_signals()` once after `Celery(...)`
construction.

Cache location
--------------
Arelle writes resolved taxonomy schemas to `ARELLE_CACHE_DIR` if set,
otherwise `~/.config/arelle/cache` (Linux/macOS) or
`%LOCALAPPDATA%/Arelle/cache` (Windows). First-time resolution of the
IDX taxonomy downloads 50-200 MB of IFRS/PSAK schemas.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any

from shared.structured_json_logger import get_logger

if TYPE_CHECKING:
    from arelle.Cntlr import Cntlr

logger = get_logger(__name__)

_controller: Cntlr | None = None
_init_lock = threading.Lock()
_signals_registered = False


def get_cntlr() -> Cntlr:
    """Return the process-local Arelle controller, initializing lazily.

    Double-checked locking — safe under prefork (no contention) and
    defensive under other pool types (still dangerous, but at least the
    init itself won't race).
    """
    global _controller
    if _controller is None:
        with _init_lock:
            if _controller is None:
                _controller = _build_controller()
    return _controller


def _build_controller() -> Cntlr:
    """Construct a fresh headless `Cntlr` with backend-appropriate defaults."""
    import os

    from arelle.Cntlr import Cntlr

    cache_dir_env = os.environ.get("ARELLE_CACHE_DIR")
    cntlr = Cntlr(hasGui=False, logFileName=None)

    if cache_dir_env:
        cache_path = Path(cache_dir_env)
        cache_path.mkdir(parents=True, exist_ok=True)
        try:
            cntlr.webCache.cacheDir = str(cache_path)
        except AttributeError:
            logger.warning(
                "arelle_cache_dir_not_settable",
                requested=str(cache_path),
            )

    if cntlr.logger is not None:
        cntlr.logger.setLevel(logging.WARNING)

    logger.info(
        "arelle_controller_initialized",
        cache_dir=getattr(cntlr.webCache, "cacheDir", "default"),
    )
    return cntlr


def shutdown_cntlr() -> None:
    """Release controller resources. Idempotent."""
    global _controller
    if _controller is None:
        return
    try:
        _controller.close()
    except (AttributeError, RuntimeError) as exc:
        logger.warning("arelle_controller_close_failed", error=str(exc))
    _controller = None
    logger.info("arelle_controller_shutdown")


def register_celery_signals() -> None:
    """Wire Arelle lifecycle to Celery worker-process signals.

    Called once from `celery_tasks.py` after the Celery app is built.
    Subsequent calls are no-ops. Safe to import without touching Celery
    until this function runs.
    """
    global _signals_registered
    if _signals_registered:
        return

    from celery.signals import worker_process_init, worker_process_shutdown

    @worker_process_init.connect  # type: ignore[misc]
    def _arelle_worker_init(**_: Any) -> None:
        try:
            get_cntlr()
        except Exception as exc:
            logger.error(
                "arelle_worker_init_failed",
                error=str(exc),
                error_type=type(exc).__name__,
            )
            raise

    @worker_process_shutdown.connect  # type: ignore[misc]
    def _arelle_worker_shutdown(**_: Any) -> None:
        shutdown_cntlr()

    _signals_registered = True
    logger.info("arelle_celery_signals_registered")
