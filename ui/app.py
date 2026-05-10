import asyncio
import flet as ft
import logging

from core.state import AppState
from ui.pages.config_page import build_config_page
from ui.pages.stats_page import build_stats_page

logger = logging.getLogger("trae_proxy")


def run_ui(app_state: AppState, on_toggle_service=None):
    assert on_toggle_service is not None
    def main(page: ft.Page):
        page.title = "Trae Proxy"
        page.theme_mode = ft.ThemeMode.SYSTEM
        page.window.width = 900
        page.window.height = 600
        page.padding = 0
        page.theme = ft.Theme(font_family="Microsoft YaHei")

        status_dot = ft.Text("●", size=16, color=ft.Colors.RED)
        status_label = ft.Text("服务: 已停止", size=14, color=ft.Colors.RED)
        req_label = ft.Text("请求: 0", size=14)

        log_view = ft.ListView(expand=True, spacing=2, padding=16, auto_scroll=True)

        start_btn = ft.TextButton("启动服务", on_click=lambda e: on_toggle_service(restart=True))
        stop_btn = ft.TextButton("关闭服务", on_click=lambda e: on_toggle_service(restart=False))

        config_content = build_config_page(app_state)
        stats_content, refresh_stats = build_stats_page(app_state)

        overview_tab = ft.Container(content=log_view, expand=True, visible=True)
        stats_tab = ft.Container(content=stats_content, expand=True, visible=False)
        config_tab = ft.Container(content=config_content, expand=True, visible=False)

        closing = False
        last_log_len = 0
        max_log_lines = 200

        def refresh_status():
            running = app_state.is_service_running()
            status_dot.color = ft.Colors.GREEN if running else ft.Colors.RED
            status_label.value = f"服务: {'运行中' if running else '已停止'}"
            status_label.color = ft.Colors.GREEN if running else ft.Colors.RED
            req_label.value = f"请求: {app_state.request_count}"
            start_btn.content = "重启服务" if running else "启动服务"
            stop_btn.visible = running

        def refresh_logs():
            nonlocal last_log_len
            logs = app_state.get_logs()
            if len(logs) < last_log_len:
                last_log_len = 0
                log_view.controls.clear()
            new_logs = logs[last_log_len:]
            if not new_logs:
                return
            for line in new_logs:
                log_view.controls.append(ft.Text(line, size=12, selectable=True, font_family="Consolas"))
            last_log_len = len(logs)
            if len(log_view.controls) > max_log_lines:
                overflow = len(log_view.controls) - max_log_lines
                del log_view.controls[:overflow]

        async def ui_updater():
            nonlocal closing
            while True:
                try:
                    if app_state.exiting:
                        if not closing:
                            closing = True
                            page.window.close()
                        break
                    refresh_status()
                    refresh_stats()
                    refresh_logs()
                    page.update()
                    await asyncio.sleep(1)
                except Exception as ex:
                    logger.exception(f"UI 刷新失败: {ex}")
                    await asyncio.sleep(1)

        def clear_logs(e):
            nonlocal last_log_len
            try:
                app_state.logs.clear()
            except Exception:
                pass
            log_view.controls.clear()
            last_log_len = 0
            page.update()

        def on_tab_change(e):
            idx = e.control.selected_index
            overview_tab.visible = idx == 0
            stats_tab.visible = idx == 1
            config_tab.visible = idx == 2
            if idx == 1:
                refresh_stats()
            page.update()

        header = ft.Container(
            content=ft.Row(
                controls=[
                    status_dot,
                    status_label,
                    ft.VerticalDivider(width=1),
                    req_label,
                    ft.Container(expand=True),
                    start_btn,
                    stop_btn,
                    ft.TextButton(
                        "清空日志",
                        on_click=clear_logs,
                        style=ft.ButtonStyle(padding=5),
                    ),
                ],
                spacing=8,
            ),
            padding=ft.padding.symmetric(horizontal=16, vertical=8),
            border=ft.border.only(
                bottom=ft.border.BorderSide(1, ft.Colors.OUTLINE)
            ),
        )

        tab_bar = ft.TabBar(
            tabs=[
                ft.Tab(label="概览"),
                ft.Tab(label="统计"),
                ft.Tab(label="配置"),
            ],
        )

        tabs = ft.Tabs(
            content=tab_bar,
            length=3,
            selected_index=0,
            on_change=on_tab_change,
        )

        page.add(
            ft.Column(
                controls=[
                    header,
                    tabs,
                    overview_tab,
                    stats_tab,
                    config_tab,
                ],
                expand=True,
                spacing=0,
            )
        )

        page.run_task(ui_updater)

    ft.app(target=main)
