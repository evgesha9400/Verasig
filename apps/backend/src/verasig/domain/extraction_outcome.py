"""Extraction outcome contract shared by extraction and storage."""

from dataclasses import dataclass

from verasig.domain.signal import ExtractedSignal, UnrecognizedSignal


@dataclass
class ExtractOutcome:
    signal: ExtractedSignal | None = None
    unrecognized: UnrecognizedSignal | None = None
