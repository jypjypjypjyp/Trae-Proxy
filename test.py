import os
import requests
import urllib3
urllib3.disable_warnings()

auth_token = os.environ.get('ANTHROPIC_AUTH_TOKEN', '')

r = requests.post('https://api.openai.com/v1/chat/completions',
    json={
        'model': 'glm-5.1',
        'messages': [{'role': 'user', 'content': 'Test'}],
    },
    headers={
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {auth_token}',
    },
    verify=True,
)
print('Status:', r.status_code)
print('Model:', r.json().get('model'))
print('Content:', r.json()['choices'][0]['message']['content'][:100])
