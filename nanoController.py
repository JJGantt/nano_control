import os
from dotenv import load_dotenv

load_dotenv()

nanoleaf_config = {
    key: value for key, value in os.environ.items() if key.startswith("NANO_")
}

class NanoController:
    def __init__(self, api_key, ip_address, port, kasa, govee):
        self.kasa = kasa
        self.govee = govee
        self.auth_token = api_key
        self.ip_address = ip_address
        self.port = port
        self.panels = []
        self.state_dict = {i: [(0, 0, 0, 1)] for i in range(len(self.panels))}

        self.timer_task = None
        self.effect = "Cocoa Beach"
        self.state = {
            "brightness" : 0, 
            "effect" : "Cocoa Beach"
        }
        self.state = NanoState()
        self.get_panels()

    @property
    def base_url(self):
        return f"http://{self.ip_address}:{self.port}/api/v1/{self.auth_token}"