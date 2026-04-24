import flet as ft
import threading
from core.state import AppState
from core.tray import TrayThread


def run_ui(app_state: AppState, tray: TrayThread):
    def main(page: ft.Page):
        page.title = "Trae Proxy"
        page.theme_mode = ft.ThemeMode.SYSTEM
        page.window_width = 1100
        page.window_height = 720
        page.padding = 0

        # 页面关闭事件：隐藏到托盘而不是退出
        def on_window_event(e):
            if e.data == ft.WindowEventType.CLOSE:
                if app_state.exiting:
                    page.window.prevent_close = False
                    return
                page.window.visible = False
                page.update()

        page.window.on_event = on_window_event
        page.window.prevent_close = True

        # 当前页面索引
        current_index = 0

        # 状态栏
        status_text = ft.Text("服务: 已停止", size=12, color=ft.Colors.RED)
        port_text = ft.Text("端口: -", size=12)
        backend_text = ft.Text("后端: -", size=12)
        req_text = ft.Text("请求: 0", size=12)

        status_bar = ft.Row(
            [status_text, ft.Text(" | ", size=12), port_text, ft.Text(" | ", size=12),
             backend_text, ft.Text(" | ", size=12), req_text],
            spacing=4,
        )

        # 概览页内容
        status_label = ft.Text("已停止", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.RED)
        req_label = ft.Text("0", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE)
        backend_label = ft.Text("-", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN)

        stats_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("后端")),
                ft.DataColumn(ft.Text("请求")),
                ft.DataColumn(ft.Text("成功率")),
                ft.DataColumn(ft.Text("延迟")),
                ft.DataColumn(ft.Text("Token/s")),
            ],
            rows=[],
        )

        overview_content = ft.Column(
            [
                ft.Text("概览", size=20, weight=ft.FontWeight.BOLD),
                ft.Row(
                    [
                        ft.Column([ft.Text("服务状态", size=12), status_label], spacing=4),
                        ft.Column([ft.Text("累计请求", size=12), req_label], spacing=4),
                        ft.Column([ft.Text("活跃后端", size=12), backend_label], spacing=4),
                    ],
                    spacing=20,
                ),
                ft.Text("模型性能", size=16, weight=ft.FontWeight.BOLD),
                stats_table,
            ],
            spacing=16,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )

        # 配置页内容
        config_content = ft.Column(
            [ft.Text("配置管理", size=20, weight=ft.FontWeight.BOLD)],
            spacing=16, expand=True, scroll=ft.ScrollMode.AUTO,
        )

        # 日志页内容
        log_text = ft.TextField(
            multiline=True, read_only=True, min_lines=15,
            expand=True, border_color=ft.Colors.OUTLINE,
        )
        logs_content = ft.Column(
            [ft.Text("日志", size=20, weight=ft.FontWeight.BOLD), log_text],
            spacing=16, expand=True,
        )

        # 工具页内容
        tools_content = ft.Column(
            [ft.Text("工具", size=20, weight=ft.FontWeight.BOLD)],
            spacing=16, expand=True, scroll=ft.ScrollMode.AUTO,
        )

        contents = [overview_content, config_content, logs_content, tools_content]
        content_area = ft.Container(content=overview_content, expand=True, padding=20)

        # 侧边栏按钮
        def make_nav_button(label, idx):
            def on_click(e):
                nonlocal current_index
                current_index = idx
                content_area.content = contents[idx]
                content_area.update()
                # 更新按钮样式
                for i, btn in enumerate(nav_buttons):
                    btn.bgcolor = ft.Colors.PRIMARY if i == idx else None
                    btn.update()

            btn = ft.ElevatedButton(
                label,
                on_click=on_click,
                bgcolor=ft.Colors.PRIMARY if idx == 0 else None,
                width=140,
            )
            return btn

        nav_buttons = [
            make_nav_button("概览", 0),
            make_nav_button("配置", 1),
            make_nav_button("日志", 2),
            make_nav_button("工具", 3),
        ]

        sidebar = ft.Container(
            content=ft.Column(
                [
                    ft.Text("Trae Proxy", size=16, weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                    *nav_buttons,
                ],
                spacing=8,
                width=160,
            ),
            padding=10,
        )

        page.add(
            ft.Row(
                [
                    sidebar,
                    ft.VerticalDivider(width=1),
                    ft.Column(
                        [content_area, ft.Divider(height=1), status_bar],
                        expand=True, spacing=0,
                    ),
                ],
                expand=True, spacing=0,
            )
        )

        # 定时刷新
        def refresh_ui():
            try:
                running = app_state.is_service_running()
                status_label.value = "运行中" if running else "已停止"
                status_label.color = ft.Colors.GREEN if running else ft.Colors.RED
                status_text.value = f"服务: {'运行中' if running else '已停止'}"
                status_text.color = ft.Colors.GREEN if running else ft.Colors.RED
                req_label.value = str(app_state.request_count)
                req_text.value = f"请求: {app_state.request_count}"

                stats = app_state.get_stats()
                active = list(stats.keys())[0] if stats else "-"
                backend_label.value = active
                backend_text.value = f"后端: {active}"
                port_text.value = f"端口: {app_state.service_port}"

                rows = []
                for name, stat in stats.items():
                    success_rate = f"{(stat.success_count / max(stat.request_count, 1) * 100):.0f}%"
                    rows.append(ft.DataRow(cells=[
                        ft.DataCell(ft.Text(name)),
                        ft.DataCell(ft.Text(str(stat.request_count))),
                        ft.DataCell(ft.Text(success_rate)),
                        ft.DataCell(ft.Text(f"{stat.avg_latency_ms / 1000:.1f}s")),
                        ft.DataCell(ft.Text(str(int(stat.tokens_per_second)))),
                    ]))
                stats_table.rows = rows

                # 刷新日志
                logs = app_state.get_logs()
                log_text.value = "\n".join(logs[-50:])

                page.update()
            except Exception:
                pass

        def schedule():
            refresh_ui()
            threading.Timer(2.0, schedule).start()

        threading.Timer(2.0, schedule).start()

        # 托盘回调
        def show_window():
            page.window.visible = True
            page.update()

        tray.page_ref = page
        tray.on_show = show_window

    ft.app(target=main)
