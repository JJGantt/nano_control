import os
from dotenv import load_dotenv
from .api import NanoAPI
from dataclasses import dataclass
import asyncio
from functools import reduce
import math
import random

load_dotenv()

nanoleaf_config = {
    key: value for key, value in os.environ.items() if key.startswith("NANO_")
}

@dataclass
class NanoState:
    brightness: int = None
    effect: str = None
    power_state: int = None
    color_dict: dict = None

@dataclass
class Panel:
    id: int
    x: int
    y: int

class Panels:
    def __init__(self, panels):
        self.list = panels
        self.ordered_ids = self.top_to_bottom()

    def __str__(self):
        return str(self.list)

    def top_to_bottom(self):
        sorted_panels = sorted(self.list, key=lambda panel: panel.y, reverse=True)
        return [panel.id for panel in sorted_panels]

    def bottom_to_top(self):
        pass

class NanoController:
    def __init__(self, auth_token=None, ip_address=None, port=None):
        self.auth_token = auth_token or nanoleaf_config.get("NANO_AUTH_TOKEN")
        self.ip_address = ip_address or nanoleaf_config.get("NANO_IP_ADDRESS")
        self.port =  port or nanoleaf_config.get("NANO_PORT")
        self.api = NanoAPI(
            auth_token=self.auth_token, 
            ip_address=self.ip_address, 
            port=self.port)

        self.panels = Panels(self.get_panels())
        self.timer_task = None
        self.state = NanoState()

        self.color_dict = {i: [(0, 0, 0, 1)] for i in range(len(self.panels.list))}
        self.state = NanoState(color_dict=self.color_dict)

    @property
    def base_url(self):
        return f"http://{self.ip_address}:{self.port}/api/v1/{self.auth_token}"
    
    def get_auth_token(self):
        self.api.get_auth_token()

    def get_panels(self):
        layout = self.api.get_layout()

        panels = []
        for panel in layout["positionData"]:
            id = panel["panelId"]
            if id == 0:
                continue
            x = panel["x"]
            y = panel["y"]
            panel = Panel(id, x, y)
            panels.append(panel)
        return panels
    
    async def set_state(self):
        state, effects = await self.api.get_state()
        self.state.brightness = state["brightness"]["value"]    
        self.state.effect = effects["select"]
        self.state.color_dict = self.color_dict.copy()    
        self.state.effects_list = effects["effectsList"]
        
    async def set_previous_state(self):
        await self.set_brightness(self.state.brightness)
        print(f'effect: {self.state.effect}')
        if self.state.effect == "*Dynamic*":
            await self.custom(self.state.color_dict)
        else:
            await self.set_effect(self.state.effect)

    async def set_brightness(self, brightness):
        await self.api.set_brightness(brightness)

    async def set_effect(self, effect):
        await self.api.set_effect(effect)
    
    async def custom(self, color_dict, loop=True):
        for i in color_dict:
            self.color_dict[i] = color_dict[i]

        transition_totals = self.get_transition_totals(self.color_dict)
        trans_lcm = math.lcm(*transition_totals)

        panel_ids = self.panels.ordered_ids

        animation_string = f"{len(panel_ids)}"
        for i, rgbt_array in self.color_dict.items():
            mult = int(trans_lcm / transition_totals[i])          
            animation_string += f" {str(panel_ids[i])} {len(rgbt_array) * mult}" 
            rgbt_string = ""
            for r, g, b, t in rgbt_array:
                rgbt_string += f" {r} {g} {b} 0 {t}"
            rgbt_string *= mult
            animation_string += rgbt_string

        await self.api.custom(animation_string, loop)
    
    def get_transition_totals(self, color_dict):
        transition_totals = []
        for rgbt in color_dict.values():
            total = reduce(lambda x,y: x + y[3], rgbt, 0)
            transition_totals.append(total)
        return transition_totals
    
    
    
    async def timer(self, 
            seconds, 
            start_color=(0,0,255), 
            end_color=(255,174,66), 
            alarm_length=10,
            alarm_brightness=100,
            end_animation=None
            ):   
        
        await self.set_state()
        
        panel_ids = self.panels.ordered_ids    
        panel_count = len(panel_ids)
        seconds_per_panel = seconds / panel_count

        sub_ts = int(seconds_per_panel)

        #Break transitions into one second intervals becasue Nanoleaf default 
        #transition times do not allow for extended smooth transitions
        transition_array = []
        r_0, g_0, b_0 = start_color
        r_1, g_1, b_1 = end_color
        r_d, g_d, b_d = (r_1 - r_0, g_1 - g_0, b_1 - b_0)
        for sub_t in range(sub_ts):
            rgbt = (int(r_0 + sub_t * (r_d / sub_ts)),
                    int(g_0 + sub_t * (g_d / sub_ts)),
                    int(b_0 + sub_t * (b_d / sub_ts)),
                    10)
            transition_array.append(rgbt)

        start_color = [(r_0, g_0, b_0, 10)]
        end_color = [(r_1, g_1, b_1, 10)]

        start = {i: start_color for i in range(panel_count)}
        
        await self.custom(start)

        for i in range(panel_count - 1, -1, -1):
            await self.custom({i: transition_array}, loop=False)
            await asyncio.sleep(seconds_per_panel)
            await self.custom({i: end_color})

        end_animation = end_animation or self.get_end_animation()
        await self.set_brightness(alarm_brightness)
        await self.custom(end_animation)
            
        await asyncio.sleep(alarm_length)
        
        await self.set_previous_state()

    def get_end_animation(self):
        anim_dict = {}
        for p in range(len(self.panels.ordered_ids)):
            color_array = []
            for i in range(20):
                rgbt = (int(random.random() * 255), int(random.random() * 255), int(random.random() * 255), 5)
                color_array.append(rgbt)
            anim_dict[p] = color_array
        return anim_dict
    

async def main():
    nano = NanoController()
    await nano.timer(15, alarm_length=5)

if __name__ == "__main__":
    asyncio.run(main())


        