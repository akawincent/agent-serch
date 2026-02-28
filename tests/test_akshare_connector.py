from agent_search.connectors.akshare_connector import AkShareConnector


def test_map_hist_row() -> None:
    row = {
        "日期": "2026-02-27",
        "开盘": 85.36,
        "最高": 85.8,
        "最低": 82.5,
        "收盘": 83.6,
        "成交量": 1175500,
        "成交额": 9800000000,
    }
    bar = AkShareConnector.map_hist_row("002463", row)
    assert bar.symbol == "002463"
    assert bar.open == 85.36
    assert bar.close == 83.6
    assert bar.volume == 1175500
