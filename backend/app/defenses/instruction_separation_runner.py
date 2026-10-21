"""Configuration B adapter for the same one-case runner/schema used by A."""
from app.defenses.baseline_runner import FixedContextRunner
from app.defenses.instruction_separation import InstructionSeparationDefense, select_trusted_role
from app.evaluation.evidence_builder import VerifiedSources
from legacy_llm.client import LLMClient


class InstructionSeparationRunner(FixedContextRunner):
    def __init__(self, client: LLMClient, sources: VerifiedSources | None = None, *, trusted_role: str | None = None):
        role = select_trusted_role(client.adapter.capabilities, preferred=trusted_role)
        super().__init__(client, sources, defense=InstructionSeparationDefense(role))
