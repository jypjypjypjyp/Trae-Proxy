#!/usr/bin/env python3
"""打包脚本：将 Trae-Proxy 打包为 Windows 可执行程序。
运行方式：uv run python build.py 或 python build.py
"""
import os
import sys
import shutil
import subprocess
import site


def run(cmd, cwd=None):
    print(f"执行: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd)
    if result.returncode != 0:
        print(f"错误: 命令失败 ({cmd})")
        sys.exit(1)


def main():
    root = os.path.dirname(os.path.abspath(__file__))
    dist_dir = os.path.join(root, "dist")
    build_dir = os.path.join(root, "build")
    spec_file = os.path.join(root, "trae-proxy.spec")
    icon_path = os.path.join(root, "asset", "logo.png")

    # 清理旧的打包产物
    for p in [dist_dir, build_dir, spec_file]:
        if os.path.exists(p):
            print(f"清理: {p}")
            if os.path.isdir(p):
                shutil.rmtree(p)
            else:
                os.remove(p)

    # 检查 PyInstaller
    try:
        import PyInstaller
    except ImportError:
        print("正在安装 PyInstaller...")
        run(f'"{sys.executable}" -m pip install pyinstaller', cwd=root)

    # 检查 Pillow（图标转换需要）
    try:
        import PIL
    except ImportError:
        print("正在安装 Pillow...")
        run(f'"{sys.executable}" -m pip install pillow', cwd=root)

    # 收集 site-packages 路径（用于 --paths）
    site_packages = site.getsitepackages()[0]

    # 构建 PyInstaller 命令
    cmd = (
        f'"{sys.executable}" -m PyInstaller'
        f' --noconfirm'
        f' --noconsole'
        f' --onedir'
        f' --name "Trae-Proxy"'
        f' --add-data "asset;asset"'
        f' --add-data "config.yaml;."'
        f' --add-data "requirements.txt;."'
        f' --paths "{site_packages}"'
        f' --hidden-import flask'
        f' --hidden-import requests'
        f' --hidden-import yaml'
        f' --hidden-import pystray'
        f' --hidden-import PIL'
        f' --hidden-import PIL._tkinter_finder'
        f' --hidden-import werkzeug'
        f' --hidden-import flet'
        f' --hidden-import flet.auth'
        f' --hidden-import flet.auth.providers'
        f' --hidden-import flet.canvas'
        f' --hidden-import flet.charts'
        f' --hidden-import flet.controls'
        f' --hidden-import flet.matplotlib_chart'
        f' --hidden-import flet.plotly_chart'
        f' --hidden-import flet.security'
        f' --hidden-import flet.shadercanvas'
        f' --hidden-import flet.types'
        f' --hidden-import flet.utils'
        f' --hidden-import flet.version'
        f' --hidden-import core.state'
        f' --hidden-import core.stats'
        f' --hidden-import core.service'
        f' --hidden-import core.tray'
        f' --hidden-import ui.app'
        f' --hidden-import ui.pages.config_page'
        f' --hidden-import ui.pages.stats_page'
        f' --hidden-import generate_certs'
        f' --hidden-import trae_proxy'
        f' --hidden-import cryptography'
        f' --collect-all flet'
        f' --collect-all flask'
        f' --collect-all werkzeug'
        f' --collect-all requests'
        f' --collect-all pystray'
        f' --collect-all PIL'
    )
    if os.path.exists(icon_path):
        cmd += f' --icon "{icon_path}"'

    cmd += f' main.py'

    run(cmd, cwd=root)

    # 打包完成后复制 config.yaml（如果 PyInstaller 没处理好）
    output_dir = os.path.join(dist_dir, "Trae-Proxy")
    if os.path.isdir(output_dir):
        for f in ["config.yaml", "requirements.txt"]:
            src = os.path.join(root, f)
            dst = os.path.join(output_dir, f)
            if os.path.exists(src) and not os.path.exists(dst):
                shutil.copy2(src, dst)
                print(f"复制: {f} -> {dst}")

    print("=" * 50)
    print("打包完成！输出目录:")
    print(f"  {output_dir}")
    print("可执行文件:")
    print(f"  {os.path.join(output_dir, 'Trae-Proxy.exe')}")
    print("=" * 50)


if __name__ == "__main__":
    main()
