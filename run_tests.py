#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Trae-Proxy 自验证脚本

用法:
    python run_tests.py          # 运行全部测试
    python run_tests.py -v       # 详细输出
    python run_tests.py -k icon  # 仅运行图标相关测试

设计原则:
1. 在每次代码修改前运行，确保无回归
2. 在 CI/自动化流程中运行
3. 测试失败时阻止合并/提交
"""

import sys
import subprocess


def main():
    args = ["pytest", "tests/", "-q"]
    if len(sys.argv) > 1:
        args.extend(sys.argv[1:])

    print("=" * 60)
    print("Trae-Proxy 自验证测试")
    print("=" * 60)

    result = subprocess.run(args, cwd=".")

    if result.returncode == 0:
        print("\n✅ 全部测试通过")
        return 0
    else:
        print("\n❌ 测试失败，请修复后再提交")
        return 1


if __name__ == "__main__":
    sys.exit(main())
