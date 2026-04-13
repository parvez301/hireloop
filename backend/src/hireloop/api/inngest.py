"""Inngest serve endpoint — POST/GET/PUT /api/v1/inngest.

In dev (INNGEST_DEV=true) signatures are not required. In prod, inngest's
fastapi integration enforces signature verification via the signing key.
"""

from __future__ import annotations

from fastapi import FastAPI

from hireloop.inngest.client import get_inngest_client
from hireloop.inngest.functions import all_functions


def mount_inngest(app: FastAPI) -> None:
    """Register Inngest serve routes on the FastAPI app."""
    import inngest.fast_api

    inngest.fast_api.serve(
        app,
        get_inngest_client(),
        all_functions(),
        serve_path="/api/v1/inngest",
    )
