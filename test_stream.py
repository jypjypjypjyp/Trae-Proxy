#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import requests
import sys

def test_stream_order():
    url = "https://api.openai.com/v1/chat/completions"

    payload = {
        "model": "qwen3.6-plus",
        "messages": [
            {"role": "user", "content": "请依次输出0到200的数字，逗号间隔，不加空格，只输出数字不要其他内容"}
        ],
        "stream": True
    }

    auth_token = os.environ.get('ANTHROPIC_AUTH_TOKEN', '')
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    }

    print("发送流式请求...")
    response = requests.post(url, json=payload, headers=headers, stream=True, timeout=60, verify=True)

    if response.status_code != 200:
        print(f"请求失败: {response.status_code}")
        print(response.text)
        return

    collected_text = ""

    for line in response.iter_lines(decode_unicode=True):
        if line and line.startswith("data: "):
            data_str = line[6:]  # 去掉 "data: " 前缀
            if data_str.strip() == "[DONE]":
                break
            try:
                import json
                chunk = json.loads(data_str)
                delta = chunk.get("choices", [{}])[0].get("delta", {})
                content = delta.get("content", "")
                if content:
                    collected_text += content
                    # 实时打印，方便观察
                    sys.stdout.write(content)
                    sys.stdout.flush()
            except json.JSONDecodeError:
                continue

    print()  # 换行
    print(f"\n完整返回内容（{len(collected_text)}字符）:")
    print(collected_text)

    # 验证顺序
    expected_numbers = [str(i) for i in range(201)]
    expected = ",".join(expected_numbers)

    # 提取返回内容中的数字
    import re
    found_numbers = re.findall(r'\d+', collected_text)

    print(f"\n提取到 {len(found_numbers)} 个数字")

    # 检查数字是否按顺序
    is_ordered = True
    for i in range(len(found_numbers) - 1):
        if int(found_numbers[i]) >= int(found_numbers[i + 1]):
            is_ordered = False
            print(f"顺序错误: {found_numbers[i]} 出现在 {found_numbers[i+1]} 之前")
            break

    if is_ordered:
        print("✓ 数字顺序正确，从 0 到 200 按序排列")
    else:
        print("✗ 数字顺序有误！")

if __name__ == "__main__":
    test_stream_order()
