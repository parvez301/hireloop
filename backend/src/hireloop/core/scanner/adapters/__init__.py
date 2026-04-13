"""Board adapters: Greenhouse, Ashby, Lever."""

from hireloop.core.scanner.adapters.base import (
    BoardAdapter,
    BoardAdapterError,
    ListingPayload,
)

__all__ = ["BoardAdapter", "BoardAdapterError", "ListingPayload"]
