from verasig.api.schemas.common import CamelModel
from verasig.services.backtesting.service import BacktestSummary


class BacktestDoneOut(CamelModel):
    score: int
    win_rate: float
    pnl: float


def done_out(summary: BacktestSummary) -> BacktestDoneOut:
    return BacktestDoneOut(
        score=summary.score,
        win_rate=summary.win_rate,
        pnl=summary.pnl,
    )
