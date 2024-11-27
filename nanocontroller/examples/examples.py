from nanocontroller import NanoController
from helpers.auth_generate import get_token
import asyncio

async def main():

    # Run this method in the time window outlined below to return auth_token
    get_token(ip_address, port)  # Port defaults to "16021". It is recommended still attempt to discover port independently    
    '''
    A user is authorized to access the OpenAPI if they can demonstrate physical access of Panels. This is achieved by: Holding the on-off button down for 5-7 seconds until the LED starts flashing in a pattern.

    Please note that Nanoleaf Skylight does not have physical on-off button, so the OpneAPI authorization window has to open through the Nanoleaf app. On the Nanoleaf mobile app, you can open that window by going to the device settings of your paired Nanoleaf Skylight and clicking on "Connect to API".
    '''    

    nano = NanoController(
    ip_address="172.20.7.17",       # Typically written on back of device, found in app, or through network scan
    port="16021",                   # "16021" is default port. 
    latitude=28.5383,               # Optional lattitude and longitude, required for weather functions. Can be changed after initialization with "set_location".
    longitude=-81.3792,
    )

    nano.get_brightness()
    nano.get_effect()
    nano.get_effects_list()         # Get list of available effects that have been downloaded in app
    nano.get_state()                # Get all states

    nano.set_brightness()
    nano.set_effect()


    '''
    This is the key component of this package to create custom functionality of panels. 
    Icluded in this package are prebuilt timer and weather display functionalities, 
    but other implementations are made posible by this method, 
    such as dynamic email/text notifications or other status displays of your choosing. 
    '''
    nano.custom(color_dict, loop=True)
    '''
    input: "color_dict" of the form:
    {
        0: [(r, g, b, t), (r, g, b, t), etc...]  
        1: [(r, g, b, t), (r, g, b, t), etc...]  
        etc...
    }
    Where  r, g, b are red, green, blue value definitions of a color between 0 and 255, 
    and t is the time to trasition to a given color. 
    Loop is True by default, if False then colors will remain static on final rgb value of array. 
    Keys correspond to the "order" of the panels. 
    Default order is "left_to_right" but ordering can be adjusted with nano.panels.top_to_bottem(), nano.panels.bottom_to_top(), nano.panels.right_to_left() 
    (use a combination of these methods to acheive diagonal ordering when panles are aligned equally vertically/horizontally at points)

    Partial "color_dict"s are acceptable. 
    If already in a state of custom display the dict {4: [(255, 0, 0, 10)]} will change the 5th panel to red in 1 second and leave the other panels in their current state.
    (a value of 10 for t corresponds to a 1 second transition time) 
    '''


    '''
    This is a prebuilt timer method that gradually trasitions panels from start_color to end_color one by one in the defined panel order. 
    '''
    nano.timer(
        60,                             # Required value in seconds. Must be greater than or equal to total panels.
        start_color=(0, 0, 225),        # Default blue
        end_color=(255, 174, 66),       # Default orange
        alarm_length=10,                # Default 10 seconds
        alarm_brightness=100,           # Default full brightness
        end_animation=None,             # Accepts custom "color_dict". Defaults to randomly transitioning colors. 
        end_function=None,              # Optional function to execute when timer ends. Must be asyncronous. 
        end_function_kwargs=None        # Keyword arguments for end_function
    )


    # Weather functions

    # Set the latitude/longitude of the location to display weather data for, or set when initialzing controller. 
    nano.set_location(latitude, longitude)

    # Sets each panel to display the forecast for the hour corresponding to the defined panel positions. 
    # Example: Heavy rain in three hours - the third panel will quickly flash various blues and whites. Overcast - The panel will slowly move between greyish colors. 
    nano.set_hourly_forecast()

    # Sets the panels to display precipitaion level over "hour_interval" periods. Defaults to one hour per panel
    nano.set_precipitation(hour_interval=1)

    '''
    Sets the panels to display the temperature per hour interval periosds. Defaults to one hour per panel.
    Default color schemer defined by the dictionary:
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
                "start": (125, 0, 175),    # Purple
                "end": (150, 0, 255)       # Duller purple
        },
        60: {
            "start": (0, 0, 255),      # Blue
            "end": (80, 90, 255)       # Slightly lighter blue
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
    Custom gradient dictionary can be passed to accomadate different climates.
    '''
    nano.set_temperature(hour_interval=1, gradient_dict=None)

   
if __name__ == "__main__":
    asyncio.run(main())