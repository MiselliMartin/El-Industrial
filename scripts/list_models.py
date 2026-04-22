import os, requests
from dotenv import load_dotenv
load_dotenv('/home/jorge/El-Industrial/.env')
KEY = os.getenv('GEMINI_API_KEY')
url = f'https://generativelanguage.googleapis.com/v1beta/models?key={KEY}'
res = requests.get(url).json()
for m in res.get('models', []):
    print(m['name'])
