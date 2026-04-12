import urllib.request, json, os
from bertual_api import BertualAPIClient

try:
    client = BertualAPIClient()
    token = client.login()
    print("Token obtained")
    
    endpoints = [
        f"{client.api_url}/ctacte/?cl={client.client_id}&f=2026-01-10",
        f"{client.api_url}/items/?q=&f=&cl={client.client_id}",
        f"{client.api_url}/familias",
        f"{client.api_url}/saldos/?cl={client.client_id}"
    ]
    
    for url in endpoints:
        print(f"\n--- Testing Endpoint: {url} ---")
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        try:
            with urllib.request.urlopen(req) as response:
                raw_data = response.read()
                print(f"Data size: {len(raw_data)} bytes")
                data = json.loads(raw_data.decode())
                
                # If it's a dict and has 'data', list first items
                if isinstance(data, dict):
                    print("Response keys:", list(data.keys()))
                    if "data" in data and isinstance(data["data"], list):
                        print(f"Number of items: {len(data['data'])}")
                        if len(data['data']) > 0:
                            print("First item sample:", json.dumps(data['data'][0], indent=2)[:300])
                elif isinstance(data, list):
                    print(f"List response, number of items: {len(data)}")
                    if len(data) > 0:
                        print("First item sample:", json.dumps(data[0], indent=2)[:300])
        except Exception as e:
            print(f"Endpoint failed: {e}")
            
except Exception as e:
    print(f"Error during initialization or login: {e}")

