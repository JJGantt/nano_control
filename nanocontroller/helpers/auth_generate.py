import requests

def get_token(ip_address, port=None):
    if not port:
        port="16021"
    url = f"http://{ip_address}:{port}/api/v1/new"
    response = requests.post(url)
    
    if response.status_code != 200:
        raise RuntimeError(f"Failed to pair with device: {response.text}")
    
    auth_token = response.json().get("auth_token")
    if not auth_token:
        raise RuntimeError("Failed to retrieve auth token")
    
    print(f"auth_token: {auth_token}")
    return auth_token