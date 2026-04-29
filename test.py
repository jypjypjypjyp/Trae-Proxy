import os
import requests


def test_api():
    url = "https://api.openai.com/v1/chat/completions"
    payload = {
        "model": "qwen3.5-flash",
        "messages": [
            {"role": "user", "content": "Test"}
        ]
    }
    auth_token = os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    }
    response = requests.post(url, json=payload, headers=headers, timeout=60, verify="ca\ca.crt")
    print(f"Status: {response.status_code}")
    print(f"Model: {response.json().get('model')}")
    print(f"Content: {response.json()['choices'][0]['message']['content']}")


if __name__ == "__main__":
    test_api()
