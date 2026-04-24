import time
from core.state import AppState, BackendStat
from core.stats import estimate_tokens, RequestTracker


def test_estimate_tokens_empty():
    assert estimate_tokens("") == 0


def test_estimate_tokens_simple():
    # 简单估算：len("hello") // 3 = 5 // 3 = 1
    assert estimate_tokens("hello") == 1


def test_estimate_tokens_long():
    text = "a" * 35
    assert estimate_tokens(text) == 11  # 35 // 3 = 11


def test_request_tracker_basic():
    state = AppState()

    with RequestTracker(state, "test-backend") as tracker:
        tracker.set_input([{"content": "hello world"}])
        time.sleep(0.01)  # 模拟请求耗时

    stats = state.get_stats()
    assert "test-backend" in stats
    stat = stats["test-backend"]
    assert stat.request_count == 1
    assert stat.success_count == 1
    assert stat.error_count == 0
    assert stat.last_latency_ms >= 10  # 至少 10ms


def test_request_tracker_with_output():
    state = AppState()

    with RequestTracker(state, "test-backend") as tracker:
        tracker.set_input([{"content": "hello"}])
        tracker.set_output("world response")
        time.sleep(0.01)

    stats = state.get_stats()
    stat = stats["test-backend"]
    assert stat.output_tokens > 0
    assert stat.tokens_per_second > 0


def test_request_tracker_failure():
    state = AppState()

    try:
        with RequestTracker(state, "failing-backend") as tracker:
            tracker.set_input([{"content": "test"}])
            raise ValueError("模拟错误")
    except ValueError:
        pass

    stats = state.get_stats()
    stat = stats["failing-backend"]
    assert stat.request_count == 1
    assert stat.success_count == 0
    assert stat.error_count == 1


def test_multiple_requests_aggregate():
    state = AppState()

    for i in range(3):
        with RequestTracker(state, "agg-backend") as tracker:
            tracker.set_input([{"content": "hi"}])
            time.sleep(0.005)

    stat = state.get_stats()["agg-backend"]
    assert stat.request_count == 3
    assert stat.success_count == 3
    assert stat.avg_latency_ms > 0
    assert stat.total_latency_ms > 0
