import flet as ft
from core.state import AppState


class OverviewPage(ft.Column):
    def __init__(self, app_state: AppState):
        super().__init__()
        self.app_state = app_state
        self.expand = True
        self.spacing = 20
        self.padding = 20

        self.status_text = ft.Text("已停止", size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.RED)
        self.req_text = ft.Text("0", size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE)
        self.backend_text = ft.Text("-", size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN)

        # 状态卡片
        self.status_card = self._build_card("服务状态", self.status_text, 'POWER_SETTINGS_NEW', ft.Colors.RED)
        self.req_card = self._build_card("累计请求", self.req_text, 'TRENDING_UP', ft.Colors.BLUE)
        self.backend_card = self._build_card("活跃后端", self.backend_text, 'MODEL_TRAINING', ft.Colors.GREEN)

        # 模型性能表格
        self.stats_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("后端名称")),
                ft.DataColumn(ft.Text("状态")),
                ft.DataColumn(ft.Text("请求数")),
                ft.DataColumn(ft.Text("成功率")),
                ft.DataColumn(ft.Text("平均延迟")),
                ft.DataColumn(ft.Text("输入Token")),
                ft.DataColumn(ft.Text("输出Token")),
                ft.DataColumn(ft.Text("Token/s")),
                ft.DataColumn(ft.Text("最近请求")),
            ],
            rows=[],
            border=ft.border.all(1, ft.Colors.OUTLINE),
            border_radius=8,
            heading_row_color=ft.Colors.SURFACE_CONTAINER,
            data_row_min_height=40,
        )

        self.controls = [
            ft.Text("概览", size=24, weight=ft.FontWeight.BOLD),
            ft.Row(
                [self.status_card, self.req_card, self.backend_card],
                spacing=16,
                alignment=ft.MainAxisAlignment.START,
            ),
            ft.Text("模型性能", size=18, weight=ft.FontWeight.BOLD),
            ft.Container(
                content=self.stats_table,
                border_radius=8,
                expand=True,
            ),
        ]

    def _build_card(self, title, value_control, icon, color):
        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [ft.Icon(icon, color=color, size=28), ft.Text(title, size=14, color=ft.Colors.ON_SURFACE_VARIANT)],
                        spacing=8,
                    ),
                    value_control,
                ],
                spacing=8,
                alignment=ft.MainAxisAlignment.START,
            ),
            padding=16,
            width=180,
            height=100,
            bgcolor=ft.Colors.SURFACE,
            border_radius=8,
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
        )

    def refresh(self):
        running = self.app_state.is_service_running()
        self.status_text.value = "运行中" if running else "已停止"
        self.status_text.color = ft.Colors.GREEN if running else ft.Colors.RED
        self.req_text.value = str(self.app_state.request_count)

        stats = self.app_state.get_stats()
        active = list(stats.keys())[0] if stats else "-"
        self.backend_text.value = active

        rows = []
        for name, stat in stats.items():
            success_rate = f"{(stat.success_count / stat.request_count * 100):.0f}%" if stat.request_count > 0 else "0%"
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(name)),
                        ft.DataCell(ft.Text("正常" if stat.error_count == 0 or stat.success_count > stat.error_count else "异常")),
                        ft.DataCell(ft.Text(str(stat.request_count))),
                        ft.DataCell(ft.Text(success_rate)),
                        ft.DataCell(ft.Text(f"{stat.avg_latency_ms / 1000:.1f}s")),
                        ft.DataCell(ft.Text(f"{stat.input_tokens / 1000:.1f}K")),
                        ft.DataCell(ft.Text(f"{stat.output_tokens / 1000:.1f}K")),
                        ft.DataCell(ft.Text(str(int(stat.tokens_per_second)))),
                        ft.DataCell(ft.Text(stat.last_request_time)),
                    ]
                )
            )
        self.stats_table.rows = rows
