"""Wire schemas for Mining Confirm (ADR 0015).

Confirm is miner-based: the browser reviews the mined template families and POSTs
the ``template_key``s it accepted. The backend re-mines the feed's stored messages
(byte-identical port) and persists the matching families' signals — so the wire
shape carries only the accepted keys, never compiled rules or extractor code.
"""

from verasig.foundation.http.schemas import CamelModel


class MiningConfirmIn(CamelModel):
    accepted_template_keys: list[str] = []


class MiningConfirmOut(CamelModel):
    feed_status: str
    templates_accepted: int
    signals_extracted: int
