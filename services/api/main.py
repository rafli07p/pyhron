"""Enthropy API entrypoint.

Provides the ASGI ``app`` instance used by uvicorn::

    uvicorn services.api.main:app --host 0.0.0.0 --port 8000
"""

from services.api.rest_gateway import create_rest_app

app = create_rest_app()
