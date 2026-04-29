import threading
from core.state import AppState, BackendStat


def test_app_state_defaults():
    state = AppState()
    assert state.service_running is False
    assert state.service_port == 443
    assert state.request_count == 0
    assert state.config_modified is False
    assert len(state.backend_stats) == 0


def test_update_and_get_stat():
    state = AppState()
    stat = BackendStat(name="test-backend", request_count=5, success_count=4)
    state.update_stat("test-backend", stat)

    stats = state.get_stats()
    assert "test-backend" in stats
    assert stats["test-backend"].request_count == 5
    assert stats["test-backend"].success_count == 4


def test_thread_safety():
    """多线程并发更新统计不应崩溃或丢失数据"""
    state = AppState()
    errors = []

    def worker():
        try:
            for i in range(100):
                stat = BackendStat(name="backend", request_count=i)
                state.update_stat("backend", stat)
                _ = state.get_stats()
                state.add_log(f"log {i}")
                _ = state.get_logs()
        except Exception as e:
            errors.append(str(e))

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0, f"并发操作报错: {errors}"


def test_logs_ring_buffer():
    state = AppState()
    # 写入超过 500 条日志
    for i in range(600):
        state.add_log(f"log {i}")

    logs = state.get_logs()
    assert len(logs) == 500
    assert logs[0] == "log 100"  # 最早的 100 条被丢弃
    assert logs[-1] == "log 599"


def test_set_service_running():
    state = AppState()
    state.set_service_running(True)
    assert state.is_service_running() is True
    state.set_service_running(False)
    assert state.is_service_running() is False
