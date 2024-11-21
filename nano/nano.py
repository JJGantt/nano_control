import os
from dotenv import load_dotenv
from .api import NanoAPI
from dataclasses import dataclass
import asyncio
from functools import reduce
import math
import random
from helpers.openmeteo import openmeteo
from helpers.weather_codes import weather_codes
import pandas as pd
from datetime import datetime

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
    def __init__(self, auth_token=None, ip_address=None, port=None, latitude=None, longitude=None):
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

        self.latitude = latitude or 28.5383
        self.longitude = longitude or -81.3792

    @property
    def base_url(self):
        return f"http://{self.ip_address}:{self.port}/api/v1/{self.auth_token}"
    
    def set_location(self, latitude, longitude):
        self.latitude = latitude
        self.longitude = longitude
    
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
    
    async def get_weather_df(self, latitude, longitude):
        df, sunrise, sunset = await openmeteo(latitude, longitude)
        current_utc = pd.to_datetime(datetime.now()).tz_localize('UTC')

        df = df[df['date'] >= current_utc]
        return df

    async def set_hourly_forecast(self, latitude=None, longitude=None, sunrise=6, sunset=18):
        latitude = latitude or self.latitude
        longitude = longitude or self.longitude
        df = await self.get_weather_df(latitude, longitude)

        now = datetime.now()
        current_hour = now.hour if now.minute < 30 else now.hour + 1

        panels = len(self.panels.list)
        hours = [(current_hour + i) % 24 for i in range(panels)]
        is_night = [0 if hour > sunrise and hour < sunset else 1 for hour in hours]

        codes = df["weather_code"][:panels].to_list()
        codes = [int(code) for code in codes]

        color_dict = {}
        for n in range(panels):
            code_array = weather_codes[codes[n]][is_night[n]].copy()
            random.shuffle(code_array)
            color_dict[n] = code_array 

        await self.custom(color_dict)

    async def set_precipitation(self, hour_interval=1, latitude=None, longitude=None):
        latitude = latitude or self.latitude
        longitude = longitude or self.longitude
        df = await self.get_weather_df(latitude, longitude)
        panels = len(self.panels.list)

        precips = df.groupby(df.index // hour_interval)["precipitation_probability"].mean()[:panels]
        color_dict = { i : [(0, 0, 2.55 * precip, 10)] for i, precip in enumerate(precips) }

        await self.custom(color_dict)

    async def set_temperature(self, hour_interval=1, latitude=None, longitude=None):
        latitude = latitude or self.latitude
        longitude = longitude or self.longitude
        df = await self.get_weather_df(latitude, longitude)
        df = df.reset_index()
        panels = len(self.panels.list)

        temps = df.groupby(df.index // hour_interval)["temperature_2m"].mean()[:panels]

        #temps = [69.9, 65.7, 60.65, 59.9, 51.8, 50]

        gradient_dict = {
            0: {
                "start": (255, 255, 255),  # Bright white
                "end": (255, 255, 255)     # Bright white
            },
            40: {
                "start": (255, 255, 255),  # Bright white
                "end": (200, 200, 200)     # Light white
            },
            50: {
                "start": (0, 0, 255),      # Blue
                "end": (80, 90, 255)       # Slightly lighter blue
            },
            60: {
                "start": (255, 0, 255),    # Purple
                "end": (110, 90, 200)      # Duller purple
            },
            70: {
                "start": (0, 255, 90),     # Aqua
                "end": (0, 255, 190)       # Slightly bluer aqua
            },
            80: {
                "start": (255, 255, 0),    # Bright yellow
                "end": (255, 100, 0)       # Reddish yellow
            },
            100: {
                "start": (255, 60, 0),     # Bright red-orange
                "end": (255, 0, 0)         # Red
            }
        }

        color_dict = {}
        gradient_keys = sorted(gradient_dict.keys())  # Ensure keys are sorted

        for i, temp in enumerate(temps):
            for j in range(len(gradient_keys) - 1):
                lower_bound = gradient_keys[j]
                upper_bound = gradient_keys[j + 1]
                
                if temp < upper_bound:
                    start_color = gradient_dict[lower_bound]["start"]
                    end_color = gradient_dict[lower_bound]["end"]
                    temp_range = (lower_bound, upper_bound)

                    color_dict[i] = self.gradienter(temp_range, start_color, end_color, temp) 
                    break
            else:
                color_dict[i] = [(255, 0, 0, 10)]
        
        await self.custom(color_dict)

    def gradienter(self, temp_range, start_color, end_color, temperature):
        start_temp, end_temp = temp_range

        ratio = (temperature - start_temp) / (end_temp - start_temp)

        r = int(start_color[0] + ratio * (end_color[0] - start_color[0]))
        g = int(start_color[1] + ratio * (end_color[1] - start_color[1]))
        b = int(start_color[2] + ratio * (end_color[2] - start_color[2]))

        return [(r, g, b, 10)]




async def main():
    nano = NanoController()
    await nano.set_temperature(hour_interval=24)

if __name__ == "__main__":
    asyncio.run(main())


        