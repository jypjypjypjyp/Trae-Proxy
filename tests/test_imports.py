"""
模块导入测试

确保所有自定义模块在任何修改后仍然可以正常导入。
这是防止循环依赖、缺失依赖、语法错误的最低成本防线。
"""


def test_import_trae_proxy():
    import trae_proxy
    assert hasattr(trae_proxy, "create_app")
    assert hasattr(trae_proxy, "run_server")
    assert hasattr(trae_proxy, "load_multi_backend_config")


def test_import_core_state():
    from core.state import AppState, BackendStat
    state = AppState()
    assert state.service_running is False
    assert state.request_count == 0


def test_import_core_stats():
    from core.stats import RequestTracker, estimate_tokens
    assert estimate_tokens("") == 0
    assert estimate_tokens("hello world") > 0


def test_import_core_service():
    from core.service import ServiceThread
    from core.state import AppState
    # 仅验证导入和实例化不报错
    state = AppState()
    svc = ServiceThread(state)
    assert svc is not None


def test_import_core_tray():
    from core.tray import TrayThread
    from core.state import AppState
    state = AppState()
    tray = TrayThread(state, lambda: None, lambda r=False: None, lambda: None)
    assert tray is not None


def test_import_ui_app():
    from ui.app import run_ui
    assert callable(run_ui)


def test_import_main():
    import main
    assert hasattr(main, "main")
