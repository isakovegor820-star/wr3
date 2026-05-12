from wr3_api.adapters.aderyn import AderynAdapter
from wr3_api.adapters.base import EngineAdapter
from wr3_api.adapters.heuristic_evm import HeuristicEvmAdapter
from wr3_api.adapters.heuristic_solana import HeuristicSolanaAdapter
from wr3_api.adapters.slither import SlitherAdapter
from wr3_api.adapters.wake import WakeAdapter


def default_adapters() -> list[EngineAdapter]:
    return [
        AderynAdapter(),
        WakeAdapter(),
        SlitherAdapter(),
        HeuristicEvmAdapter(),
        HeuristicSolanaAdapter(),
    ]
