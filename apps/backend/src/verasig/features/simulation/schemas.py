from verasig.features.simulation.backtesting import BacktestSummary
from verasig.foundation.http.schemas import CamelModel


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
