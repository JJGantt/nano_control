import requests
import logging
import httpx

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def handle_api_errors(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.exceptions.HTTPError as http_err:
            logger.error(f"HTTP error occurred: {http_err}")
        except requests.exceptions.RequestException as req_err:
            logger.error(f"Request error occurred: {req_err}")
        except Exception as err:
            logger.error(f"Unexpected error: {err}")
        return None
    return wrapper

class NanoAPI:
    def __init__(self, auth_token, ip_address, port):
        self.auth_token = auth_token
        self.ip_address = ip_address
        self.port = port

    @property
    def base_url(self):
        return f"http://{self.ip_address}:{self.port}/api/v1/{self.auth_token}"
    
    @handle_api_errors
    def get_auth_token(self):
        url = f"http://{self.ip_address}:{self.port}/api/v1/new"

        response = requests.post(url)
        self.auth_token = response.json()["auth_token"]

    @handle_api_errors
    def get_layout(self):
        url = f"{self.base_url}/panelLayout/layout"

        response = requests.get(url)
        response.raise_for_status()  
        layout = response.json()
        return layout
    
    @handle_api_errors
    async def get_state(self):
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/state")
        state = response.json()

        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/effects")
        effects = response.json()

        return state, effects
    
    @handle_api_errors
    async def set_effect(self, effect):
        url = f"{self.base_url}/effects/select"
        payload = {'select': effect}
        async with httpx.AsyncClient() as client:
            response = await client.put(url, json=payload)
        return response
    
    @handle_api_errors
    async def set_brightness(self, brightness, duration=2):
        url = f"{self.base_url}/state"
        payload = {'brightness': {'value': brightness, 'duration': duration}}
        async with httpx.AsyncClient() as client:
            response = await client.put(url, json=payload)
        return response
    
    @handle_api_errors
    async def set_color(self):
        pass

    @handle_api_errors
    async def set_hue(self):
        pass

    @handle_api_errors
    async def set_saturation(self):
        pass

    @handle_api_errors
    async def custom(self, animation_string, loop):
        url = f"{self.base_url}/effects"
        payload = {"write" : {"command" : "display", "animType" : "custom", "animData" : animation_string, "loop": loop, "palette":[]}}
        
        async with httpx.AsyncClient() as client:
            response = await client.put(url, json=payload)
        return response
    



