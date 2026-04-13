"""Registry of all Inngest functions served by the app."""

from __future__ import annotations

import inngest

from hireloop.inngest.batch_evaluate import register as register_batch_evaluate
from hireloop.inngest.scan_boards import register as register_scan_boards


def all_functions() -> list[inngest.Function]:
    return [register_scan_boards(), register_batch_evaluate()]
