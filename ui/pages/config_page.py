import flet as ft
import yaml
import logging
from core.state import AppState

logger = logging.getLogger('trae_proxy')

_STREAM_OPTIONS = [
    ft.dropdown.Option("null", "默认"),
    ft.dropdown.Option("true", "强制流式"),
    ft.dropdown.Option("false", "强制非流式"),
]


def build_config_page(app_state: AppState, on_navigate=None):
    config = app_state.get_config()
    refs = {}

    def _save():
        nonlocal config
        config["server"]["port"] = int(refs["port"].value)
        config["server"]["debug"] = refs["debug"].value
        config["vision_fallback"] = refs["vision"].value or None

        apis = config.get("apis", [])
        for i, api in enumerate(apis):
            prefix = f"api_{i}"
            api["active"] = refs[f"{prefix}_active"].value
            api["custom_model_id"] = (refs[f"{prefix}_custom"].value or "").strip()
            api["target_model_id"] = (refs[f"{prefix}_target"].value or "").strip()
            val = (refs[f"{prefix}_endpoint"].value or "").strip()
            api["endpoint"] = val if val else None
            raw = refs[f"{prefix}_stream"].value
            api["stream_mode"] = None if raw == "null" else (raw == "true")
            api["supports_image"] = refs[f"{prefix}_image"].value

        try:
            with open("config.yaml", "w", encoding="utf-8") as f:
                yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
            app_state.set_config(config)
            logger.info("配置已保存")
        except Exception as e:
            logger.error(f"保存配置失败: {e}")

    def _on_change(e=None):
        _save()

    server = config.get("server", {})
    apis = config.get("apis", [])

    port_field = ft.TextField(
        label="端口",
        value=str(server.get("port", 443)),
        width=120,
        on_change=_on_change,
    )
    refs["port"] = port_field

    debug_switch = ft.Switch(
        label="Debug 模式",
        value=server.get("debug", False),
        on_change=_on_change,
    )
    refs["debug"] = debug_switch

    vision_options = [ft.dropdown.Option("")]
    for api in apis:
        if not api.get("supports_image", True):
            continue
        cid = api.get("custom_model_id", "")
        if cid:
            vision_options.append(ft.dropdown.Option(cid))
    vision_dropdown = ft.Dropdown(
        label="Vision 回退模型",
        value=config.get("vision_fallback", "") or "",
        options=vision_options,
        width=350,
        on_select=_on_change,
    )
    refs["vision"] = vision_dropdown

    api_cards_container = ft.Column(spacing=0)

    def _rebuild_api_cards():
        keys = [k for k in refs if k.startswith("api_")]
        for k in keys:
            del refs[k]
        api_cards_container.controls.clear()
        apis = config.get("apis", [])
        for i, api in enumerate(apis):
            prefix = f"api_{i}"
            card = _build_api_card(i, api, prefix, refs, _on_change, on_delete=_confirm_delete)
            api_cards_container.controls.append(card)

        vision_options = [ft.dropdown.Option("")]
        for api_item in apis:
            if not api_item.get("supports_image", True):
                continue
            cid = api_item.get("custom_model_id", "")
            if cid:
                vision_options.append(ft.dropdown.Option(cid))
        refs["vision"].options = vision_options
        current = refs["vision"].value
        if current and not any(o.key == current for o in vision_options):
            refs["vision"].value = ""

    def _add_model(e):
        apis = config.get("apis", [])
        n = len(apis) + 1
        apis.append({
            "active": True,
            "custom_model_id": "",
            "target_model_id": "",
            "endpoint": None,
            "name": f"新模型 {n}",
            "stream_mode": None,
            "supports_image": True,
        })
        _rebuild_api_cards()
        _save()
        e.page.update()

    def _confirm_delete(e):
        prefix = e.control.data
        idx = int(prefix.split("_")[1])
        page = e.page
        apis = config.get("apis", [])
        if not (0 <= idx < len(apis)):
            return
        dlg = ft.AlertDialog(
            title=ft.Text("确认删除"),
            content=ft.Text(f"确定删除模型「{apis[idx].get('name', '')}」吗？"),
            actions=[
                ft.TextButton("取消", on_click=lambda e: page.pop_dialog()),
                ft.TextButton("删除", on_click=lambda e: _do_delete(idx, page)),
            ],
        )
        page.show_dialog(dlg)

    def _do_delete(idx, page):
        apis = config.get("apis", [])
        if 0 <= idx < len(apis):
            del apis[idx]
        _rebuild_api_cards()
        _save()
        page.pop_dialog()
        page.update()

    def _refresh_from_file(e):
        nonlocal config
        try:
            with open("config.yaml", "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
            app_state.set_config(config)
            refs["port"].value = str(config.get("server", {}).get("port", 443))
            refs["debug"].value = config.get("server", {}).get("debug", False)
            _rebuild_api_cards()
            refs["vision"].value = config.get("vision_fallback", "") or ""
            e.page.update()
            logger.info("配置已从文件重新加载")
        except Exception as ex:
            logger.error(f"刷新配置失败: {ex}")

    api_cards_container.controls.clear()
    _rebuild_api_cards()

    add_btn = ft.ElevatedButton("+ 添加模型", on_click=_add_model, icon=ft.Icons.ADD)

    notice = ft.Container(
        content=ft.Row([
            ft.Text(
                "配置修改后自动保存，重启服务后生效。端点或认证为空时默认从环境变量 ANTHROPIC_BASE_URL / ANTHROPIC_AUTH_TOKEN 读取",
                size=12, italic=True, color=ft.Colors.GREY_500, expand=True,
            ),
            ft.IconButton(ft.Icons.REFRESH, icon_size=16, tooltip="从文件重新加载配置", on_click=_refresh_from_file),
        ], spacing=4),
        padding=ft.padding.only(top=8, bottom=4),
    )

    return ft.Container(ft.Column(
        [
            notice,
            ft.Container(
                content=ft.Text("服务器设置", size=16, weight=ft.FontWeight.BOLD),
                padding=ft.padding.only(bottom=4),
            ),
            ft.Row([port_field, debug_switch], spacing=16),
            ft.Divider(height=16),
            ft.Container(
                content=ft.Text("Vision 回退", size=16, weight=ft.FontWeight.BOLD),
                padding=ft.padding.only(bottom=4),
            ),
            vision_dropdown,
            ft.Divider(height=16),
            ft.Container(
                content=ft.Text("后端 API 配置", size=16, weight=ft.FontWeight.BOLD),
                padding=ft.padding.only(bottom=4),
            ),
            api_cards_container,
            add_btn,
        ],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    ), padding=16)


def _build_api_card(index, api, prefix, refs, on_change, on_delete=None):
    active_switch = ft.Switch(
        value=api.get("active", True),
        on_change=on_change,
    )
    refs[f"{prefix}_active"] = active_switch

    custom_field = ft.TextField(
        label="对外模型 ID",
        value=api.get("custom_model_id", ""),
        expand=True,
        on_change=on_change,
    )
    refs[f"{prefix}_custom"] = custom_field

    target_field = ft.TextField(
        label="实际模型 ID",
        value=api.get("target_model_id", ""),
        expand=True,
        on_change=on_change,
    )
    refs[f"{prefix}_target"] = target_field

    endpoint_field = ft.TextField(
        label="API 端点",
        value=api.get("endpoint", ""),
        expand=True,
        on_change=on_change,
    )
    refs[f"{prefix}_endpoint"] = endpoint_field

    raw_stream = api.get("stream_mode")
    stream_val = "null" if raw_stream is None else str(raw_stream).lower()
    stream_dropdown = ft.Dropdown(
        label="流模式",
        value=stream_val,
        options=_STREAM_OPTIONS,
        width=140,
        on_select=on_change,
    )
    refs[f"{prefix}_stream"] = stream_dropdown

    image_switch = ft.Switch(
        label="支持图片",
        value=api.get("supports_image", True),
        on_change=on_change,
    )
    refs[f"{prefix}_image"] = image_switch

    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Text(api.get("name", f"后端 {index+1}"), size=14, weight=ft.FontWeight.BOLD),
                        ft.Container(expand=True),
                        ft.Text("激活", size=12),
                        active_switch,
                        ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_size=18, tooltip="删除", on_click=on_delete, data=prefix),
                    ],
                    spacing=4,
                ),
                ft.Row([custom_field, target_field], spacing=8),
                endpoint_field,
                ft.Row([stream_dropdown, image_switch], spacing=16),
            ],
            spacing=8,
        ),
        padding=ft.padding.all(12),
        border=ft.border.all(1, ft.Colors.OUTLINE),
        border_radius=8,
        margin=ft.margin.only(bottom=8),
    )
