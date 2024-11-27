import os
from dotenv import load_dotenv
from .api import NanoAPI
from dataclasses import dataclass
import asyncio
from functools import reduce
import math
from random import random, shuffle
from .helpers.openmeteo import openmeteo
from .helpers.weather_codes import weather_codes
import pandas as pd
from datetime import datetime
from .helpers.colors import *


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
    effects_list: list = None

@dataclass
class Panel:
    id: int
    x: int
    y: int

class Panels:
    def __init__(self, panels: list[Panel]) -> None:
        self.list = panels
        self.ordered_ids = self.top_to_bottom()

    def __str__(self) -> str:
        return str(self.list)

    def top_to_bottom(self) -> list[int]:
        sorted_panels = sorted(self.list, key=lambda panel: panel.y, reverse=True)
        return [panel.id for panel in sorted_panels]

    def bottom_to_top(self) -> list[int]:
        sorted_panels = sorted(self.list, key=lambda panel: panel.y)
        return [panel.id for panel in sorted_panels]
    
    def left_to_right(self) -> list[int]:
        sorted_panels = sorted(self.list, key=lambda panel: panel.x)
        return [panel.id for panel in sorted_panels]
    
    def right_to_left(self) -> list[int]:
        sorted_panels = sorted(self.list, key=lambda panel: panel.x, reverse=True)
        return [panel.id for panel in sorted_panels]
    
    def custom_sort(self, orderded_ids) -> None:
        self.ordered_ids = [orderded_ids]

class Frame:
    def __init__(
        self, 
        red: int, 
        green: int, 
        blue: int, 
        t: int = 10
    ) -> None:
        self.red = red
        self.green = green
        self.blue = blue
        self.transition = t

class NanoController:
    def __init__(
            self, 
            auth_token: str = None, 
            ip_address: str = None, 
            port: str = None, 
            latitude: float = None, 
            longitude: float = None
    ) -> None:
        self.auth_token = auth_token or nanoleaf_config.get("NANO_AUTH_TOKEN") 
        self.ip_address = ip_address or nanoleaf_config.get("NANO_IP_ADDRESS")
        self.port =  port or nanoleaf_config.get("NANO_PORT") or "16021"
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

        self.hex_task = None
        self.weather_task = None

    @property
    def base_url(self) -> str:
        return f"http://{self.ip_address}:{self.port}/api/v1/{self.auth_token}"
    
    def set_location(self, latitude: float, longitude: float) -> None:
        self.latitude = latitude
        self.longitude = longitude
    
    def get_auth_token(self) -> str:
        return self.api.get_auth_token()

    def get_panels(self) -> None:
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
    
    async def set_state(self) -> None:
        state, effects = await self.api.get_state()
        self.state.brightness = state["brightness"]["value"]    
        self.state.effect = effects["select"]
        self.state.color_dict = self.color_dict.copy()    
        self.state.effects_list = effects["effectsList"]

    async def get_state(self) -> str:
        await self.set_state()
        return self.state
        
    async def set_previous_state(self) -> None:
        await self.set_brightness(self.state.brightness)
        print(f'effect: {self.state.effect}')
        if self.state.effect == "*Dynamic*":
            await self.custom(self.state.color_dict)
        else:
            await self.set_effect(self.state.effect)

    async def cancel_task(self) -> None:
        if self.hex_task and not self.hex_task.done():
            self.hex_task.cancel()  
            self.set_previous_state()

    async def set_brightness(self, brightness: int) -> None:
        await self.api.set_brightness(brightness)

    async def get_brightness(self) -> int:
        await self.set_state()
        return self.state.brightness

    async def set_effect(self, effect: str):
        await self.api.set_effect(effect)

    async def get_effect(self) -> str:
        await self.set_state()
        return self.state.effect

    async def get_effects_list(self) -> list[str]:
        await self.set_state()
        return self.state.effects_list
    
    def transform_color_dict(
            self, 
            color_dict: dict, 
            color_range: int = 60,
            color_factor: int = 50,
            transition_average: int = 20,
            transition_factor: int = 2
    ) -> dict:
        '''
        {0: [(138, 0, 236, 10)], 1: [(62, 69, 255, 10)], 2: [(43, 49, 255, 10)], 3: [(24, 27, 255, 10)], 4: [(12, 14, 255, 10)], 5: [(142, 142, 142, 10)]}
        '''
        

        transformed_color_dict = {}
        for i, rgbt in color_dict.items():
            r, g, b, _ = rgbt[0]

            color_list = []
            for n in range(6):
                #change color randomly
                '''
                r = r - (color_range / 2) + random() * color_range
                r = int(max(0, min(r, 255)))
                g = g - (color_range / 2) + random() * color_range
                g = int(max(0, min(g, 255)))
                b = b - (color_range / 2) + random() * color_range
                b = int(max(0, min(b, 255)))
                '''

                #change brightness randomly
                factor = ( (0 - color_factor / 2) + (random() * color_factor) ) * .01

                r = max(0, min(int(r + r * factor), 255))
                g = max(0, min(int(g + g * factor), 255))
                b = max(0, min(int(b + b * factor), 255))

                t = 10 + int((random() * transition_factor)) * 10

                color_list.append((r,g,b,t))
            transformed_color_dict[i] = color_list
        return transformed_color_dict       


    async def custom(
            self, 
            color_dict: dict, 
            loop: bool = True
    ) -> None:
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
    
    def get_transition_totals(self, color_dict: dict) -> list[int]:
        transition_totals = []
        for rgbt in color_dict.values():
            total = reduce(lambda x,y: x + y[3], rgbt, 0)
            transition_totals.append(total)
        return transition_totals
    
    async def timer(self, 
            seconds: int, 
            start_color: tuple[int, int, int] = BLUE, 
            end_color: tuple[int, int, int] = ORANGE, 
            alarm_length: int = 10,
            alarm_brightness: int = 100,
            end_animation: dict | None = None,
            end_function: object | None = None,
            end_function_kwargs: dict | None = None
    ) -> None:   
        
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
            
        bright_task = asyncio.create_task(self.set_brightness(alarm_brightness))
        end_anim_task = asyncio.create_task(self.custom(end_animation)) 
        end_tasks = [bright_task, end_anim_task]
        if end_function:
            end_tasks.append(asyncio.create_task(end_function(**end_function_kwargs)))
        await asyncio.gather(*end_tasks)

        await asyncio.sleep(alarm_length)
        
        await self.set_previous_state()

    def get_end_animation(self) -> dict:
        anim_dict = {}
        for p in range(len(self.panels.ordered_ids)):
            color_array = []
            for i in range(20):
                rgbt = (int(random() * 255), int(random() * 255), int(random() * 255), 5)
                color_array.append(rgbt)
            anim_dict[p] = color_array
        return anim_dict

    def cancel_timer(self) -> None:
        if self.timer_task and not self.timer_task.done():
            self.timer_task.cancel()  
            self.set_previous_state()
    
    async def get_weather_df(
            self, 
            latitude: int, 
            longitude: int
    ) -> pd.DataFrame:
        df, sunrise, sunset = await openmeteo(latitude, longitude)
        current_utc = pd.Timestamp.now(tz="UTC")

        df = df[df['date'] >= current_utc]
        return df

    async def set_hourly_forecast(
            self, 
            latitude: float | None = None, 
            longitude: float | None = None, 
            sunrise: int = 6, 
            sunset: int = 18,
    ) -> None:
        await self.set_state()
        latitude = latitude or self.latitude
        longitude = longitude or self.longitude
        df = await self.get_weather_df(latitude, longitude)

        now = datetime.now()
        current_hour = now.hour if now.minute < 30 else now.hour + 1

        print(now, current_hour)

        panels = len(self.panels.list)
        hours = [(current_hour + i) % 24 for i in range(panels)]
        is_night = [0 if hour > sunrise and hour < sunset else 1 for hour in hours]


        codes = df["weather_code"][:panels].to_list()
        codes = [int(code) for code in codes]

        is_night = [0, 0, 0, 0, 0, 1]
        codes = [0, 3, 51, 55, 61, 82]

        color_dict = {}
        for n in range(panels):
            code_array = weather_codes[codes[n]][is_night[n]].copy()
            shuffle(code_array)
            color_dict[n] = code_array 

        print(color_dict)

        await self.custom(color_dict)

    async def set_precipitation(
            self, 
            hour_interval: int = 1, 
            latitude: float | None = None, 
            longitude: float | None = None,
            max_color: tuple[int, int, int] = BLUE,
            min_color: tuple[int, int, int] = YELLOW
    ) -> None:
        await self.set_state()
        latitude = latitude or self.latitude
        longitude = longitude or self.longitude
        df = await self.get_weather_df(latitude, longitude)
        panels = len(self.panels.list)

        precips = df.groupby(df.index // hour_interval)["precipitation_probability"].mean()[:panels]

        #precips = [0, 30, 60, 100, 90, 25]

        r0, g0, b0 = min_color
        r1, g1, b1 = max_color

        color_dict = { 
            i : [(
                r0 + precip/100 * (r1 - r0),  
                g0 + precip/100 * (g1 - g0), 
                b0 + precip/100 * (b1 - b0),
                10
            )] 
            for i, precip in enumerate(precips) 
        }

        await self.custom(color_dict)

    async def set_temperature(
            self, 
            hour_interval: int = 1, 
            latitude: float | None = None, 
            longitude: float | None = None, 
            gradient_dict: dict | None = None,
    ) -> None:
        await self.set_state()
        latitude = latitude or self.latitude
        longitude = longitude or self.longitude
        df = await self.get_weather_df(latitude, longitude)
        df = df.reset_index()
        panels = len(self.panels.list)

        temps = df.groupby(df.index // hour_interval)["temperature_2m"].mean()[:panels]
        
        #print(temps)
        #temps = [40, 50, 60, 75, 85, 100]
        #temps = [45, 52, 58, 62, 68, 75]

        gradient_dict = gradient_dict or {
            0: {
                "start": (255, 255, 255),  # Bright white
                "end": (255, 255, 255)     # Bright white
            },
            40: {
                "start": (255, 255, 255),  # Bright white
                "end": (128, 128, 128)     # Light white
            },
            50: {
                "start": (125, 0, 175),    # Purple
                "end": (150, 0, 255)       # Duller purple
            },
            60: {
                "start": (0, 0, 255),      # Blue
                "end": (80, 90, 255)       # Slightly lighter blue
            },
            70: {
                "start": (0, 240, 100),     # Aqua
                "end": (0, 255, 190)        # Slightly bluer aqua
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

    def gradienter(
            self, 
            temp_range: tuple[int, int], 
            start_color: tuple[int, int, int], 
            end_color: tuple[int, int, int], 
            temperature: int
    ) -> list[tuple[int, int, int, int]]:
        start_temp, end_temp = temp_range

        ratio = (temperature - start_temp) / (end_temp - start_temp)

        r = int(start_color[0] + ratio * (end_color[0] - start_color[0]))
        g = int(start_color[1] + ratio * (end_color[1] - start_color[1]))
        b = int(start_color[2] + ratio * (end_color[2] - start_color[2]))

        return [(r, g, b, 10)]

async def main():
    nano = NanoController()
    await nano.set_precipitation(4)

if __name__ == "__main__":
    asyncio.run(main())


        