"""Negotiation module — playbook generator + service orchestrator."""

from hireloop.core.negotiation.playbook import GeneratedPlaybook, generate_negotiation_playbook
from hireloop.core.negotiation.service import NegotiationContext, NegotiationService

__all__ = [
    "GeneratedPlaybook",
    "NegotiationContext",
    "NegotiationService",
    "generate_negotiation_playbook",
]
