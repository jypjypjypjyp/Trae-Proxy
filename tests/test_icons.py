import ast
import os
import pytest
import flet as ft


UI_DIR = os.path.join(os.path.dirname(__file__), "..", "ui")
CORE_DIR = os.path.join(os.path.dirname(__file__), "..", "core")


def _find_py_files(base_dir):
    """递归查找目录下所有 .py 文件"""
    files = []
    for root, _, filenames in os.walk(base_dir):
        for f in filenames:
            if f.endswith(".py"):
                files.append(os.path.join(root, f))
    return files


def _extract_ft_icons_attribute(filepath):
    """解析 Python 文件，提取 ft.icons.XXX 属性访问"""
    usages = []
    with open(filepath, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())

    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Attribute):
                if isinstance(node.value.value, ast.Name):
                    if node.value.value.id == "ft" and node.value.attr == "icons":
                        usages.append((filepath, node.lineno, node.attr))
    return usages


def _extract_ft_colors_attribute(filepath):
    """解析 Python 文件，提取 ft.colors.XXX 属性访问（Flet 0.84 必须用 ft.Colors）"""
    usages = []
    with open(filepath, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())

    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name):
                if node.value.id == "ft" and node.attr == "colors":
                    usages.append((filepath, node.lineno))
    return usages


def _extract_ft_animation_attribute(filepath):
    """解析 Python 文件，提取 ft.animation.XXX 属性访问（Flet 0.84 必须用 ft.Animation）"""
    usages = []
    with open(filepath, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())

    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name):
                if node.value.id == "ft" and node.attr == "animation":
                    usages.append((filepath, node.lineno))
    return usages


def test_no_ft_icons_attribute_usage():
    """致命规则：禁止在 UI 代码中使用 ft.icons.XXX 属性访问方式。

    背景：Flet 在不同版本中图标 API 不稳定。
    - 旧版（~0.20）: ft.icons.DASHBOARD 可用
    - 新版（0.84+）: ft.icons 变为模块，图标名需以字符串传入，如 'DASHBOARD'
    使用 ft.icons.XXX 会导致 AttributeError，程序启动即崩溃。
    """
    all_usages = []
    for filepath in _find_py_files(UI_DIR):
        usages = _extract_ft_icons_attribute(filepath)
        all_usages.extend(usages)

    if all_usages:
        msg_lines = ["发现 ft.icons.XXX 属性访问（必须用字符串替代）："]
        for filepath, lineno, attr in all_usages:
            rel = os.path.relpath(filepath)
            msg_lines.append(f"  {rel}:{lineno}  ft.icons.{attr}")
        pytest.fail("\n".join(msg_lines))


def test_no_ft_colors_attribute_usage():
    """致命规则：禁止在代码中使用 ft.colors.XXX（小写）。

    Flet 0.84+ 使用 ft.Colors（大写C），ft.colors 不存在。
    使用 ft.colors 会导致 AttributeError，程序启动即崩溃。
    """
    all_usages = []
    dirs = [UI_DIR, CORE_DIR]
    for base_dir in dirs:
        for filepath in _find_py_files(base_dir):
            usages = _extract_ft_colors_attribute(filepath)
            all_usages.extend([(filepath, lineno) for _, lineno in usages])

    if all_usages:
        msg_lines = ["发现 ft.colors.XXX（小写，必须用 ft.Colors 替代）："]
        for filepath, lineno in all_usages:
            rel = os.path.relpath(filepath)
            msg_lines.append(f"  {rel}:{lineno}")
        pytest.fail("\n".join(msg_lines))


def test_no_ft_animation_attribute_usage():
    """致命规则：禁止在代码中使用 ft.animation.XXX。

    Flet 0.84+ 使用 ft.Animation 直接作为类，ft.animation 模块不存在。
    使用 ft.animation.Animation 会导致 AttributeError，程序启动即崩溃。
    """
    all_usages = []
    dirs = [UI_DIR, CORE_DIR]
    for base_dir in dirs:
        for filepath in _find_py_files(base_dir):
            usages = _extract_ft_animation_attribute(filepath)
            all_usages.extend([(filepath, lineno) for _, lineno in usages])

    if all_usages:
        msg_lines = ["发现 ft.animation.XXX（必须用 ft.Animation 替代）："]
        for filepath, lineno in all_usages:
            rel = os.path.relpath(filepath)
            msg_lines.append(f"  {rel}:{lineno}")
        pytest.fail("\n".join(msg_lines))


def test_all_icon_strings_are_valid():
    """验证 UI 代码中所有字符串形式的图标名称都是 Flet 支持的合法图标。"""
    invalid = []
    valid_names = set(dir(ft.icons.Icons))

    for filepath in _find_py_files(UI_DIR):
        with open(filepath, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())

        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                icon_name = node.value
                # 简单启发式：全大写且带下划线，可能是图标名
                if icon_name.isupper() and "_" in icon_name and len(icon_name) > 3:
                    if icon_name not in valid_names:
                        rel = os.path.relpath(filepath)
                        invalid.append((rel, node.lineno, icon_name))

    if invalid:
        msg_lines = ["发现不合法的图标名称："]
        for rel, lineno, name in invalid:
            msg_lines.append(f"  {rel}:{lineno}  '{name}'")
        pytest.fail("\n".join(msg_lines))


def test_all_ft_colors_are_valid():
    """验证所有 ft.Colors.XXX 引用都是 Flet 支持的合法颜色名。"""
    valid_colors = set(dir(ft.Colors))
    invalid = []

    dirs = [UI_DIR, CORE_DIR]
    for base_dir in dirs:
        for filepath in _find_py_files(base_dir):
            with open(filepath, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())

            for node in ast.walk(tree):
                if isinstance(node, ast.Attribute):
                    if isinstance(node.value, ast.Attribute):
                        if isinstance(node.value.value, ast.Name):
                            if node.value.value.id == "ft" and node.value.attr == "Colors":
                                color = node.attr
                                if color not in valid_colors:
                                    rel = os.path.relpath(filepath)
                                    invalid.append((rel, node.lineno, color))

    if invalid:
        msg_lines = ["发现不合法的 Flet 颜色名："]
        for rel, lineno, color in invalid:
            msg_lines.append(f"  {rel}:{lineno}  ft.Colors.{color}")
        pytest.fail("\n".join(msg_lines))
