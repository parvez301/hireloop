"""Feedback service — generic write-path with per-resource ownership validators."""

from hireloop.core.feedback.service import (
    FeedbackResourceNotFound,
    FeedbackService,
    InvalidFeedback,
)

__all__ = ["FeedbackService", "FeedbackResourceNotFound", "InvalidFeedback"]
