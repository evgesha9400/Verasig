"""Extraction outcome contract shared by extraction and storage."""

from dataclasses import dataclass, field

from verasig.domain.drift import ParserDriftWarning
from verasig.domain.signal import ExtractedSignal, UnrecognizedSignal


@dataclass
class ExtractOutcome:
    signal: ExtractedSignal | None = None
    unrecognized: UnrecognizedSignal | None = None
    drift_warnings: list[ParserDriftWarning] = field(default_factory=list)
