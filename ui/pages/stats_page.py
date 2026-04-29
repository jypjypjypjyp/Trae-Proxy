import flet as ft
import logging
from core.state import AppState

logger = logging.getLogger('trae_proxy')

_COLUMNS = [
    ("模型", "name", False),
    ("请求数", "request_count", True),
    ("成功率%", "success_rate", True),
    ("平均延迟(ms)", "avg_latency_ms", True),
    ("输出Token/s", "tokens_per_second", True),
    ("输入Token", "input_tokens", True),
    ("输出Token", "output_tokens", True),
    ("最后请求", "last_request_time", False),
]


def build_stats_page(app_state: AppState):
    sort_col = 0
    sort_asc = True

    def _build_data():
        raw_stats = app_state.get_stats()
        stats = raw_stats.values()
        rows = []
        for s in stats:
            rate = 0.0
            if s.request_count > 0:
                rate = round(s.success_count / s.request_count * 100, 1)
            rows.append({
                "name": s.name,
                "request_count": s.request_count,
                "success_rate": rate,
                "avg_latency_ms": round(s.avg_latency_ms, 0),
                "tokens_per_second": s.tokens_per_second,
                "input_tokens": s.input_tokens,
                "output_tokens": s.output_tokens,
                "last_request_time": s.last_request_time,
            })
        key_name = _COLUMNS[sort_col][1]
        rows.sort(key=lambda r: (r.get(key_name, "") or ""), reverse=not sort_asc)
        return rows

    def _build_rows():
        return [
            ft.DataRow(cells=[
                ft.DataCell(ft.Text(str(r.get(k, "")), size=12))
                for _, k, _ in _COLUMNS
            ]) for r in _build_data()
        ]

    table = ft.DataTable(
        column_spacing=20,
        horizontal_margin=10,
        divider_thickness=0,
        heading_row_color=ft.Colors.SURFACE_CONTAINER,
        sort_column_index=0,
        sort_ascending=True,
        columns=[
            ft.DataColumn(
                label=ft.Text(label, size=12, weight=ft.FontWeight.BOLD),
                numeric=numeric,
                on_sort=lambda e, idx=i: _on_sort(idx),
            )
            for i, (label, _, numeric) in enumerate(_COLUMNS)
        ],
        rows=[],
    )

    def refresh():
        nonlocal sort_col, sort_asc
        rows = _build_rows()
        table.rows = rows
        table.sort_column_index = sort_col
        table.sort_ascending = sort_asc
        try:
            table.update()
        except RuntimeError:
            pass

    def _on_sort(idx):
        nonlocal sort_col, sort_asc
        if sort_col == idx:
            sort_asc = not sort_asc
        else:
            sort_col = idx
            sort_asc = False
        refresh()

    refresh()

    return ft.Column(
        [ft.Container(content=table, expand=True, padding=16)],
        expand=True, scroll=ft.ScrollMode.AUTO,
    ), refresh
