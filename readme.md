# NanoController Python Package

## Overview

The nanocontroller package allows you to interface with Nanoleaf devices, providing functionality for controlling individual lights programmatically, setting timers, and displaying weather information. 

---

## Installation
 
```bash
pip install nanocontroller
```

---

## Authorization  

To use the Nanoleaf OpenAPI, physical access to the device is required:

Hold the on-off button for 5-7 seconds until the LED starts flashing in a pattern or open the authorization window via the Nanoleaf mobile app by navigating to device settings and selecting "Connect to API."

Run this function to obtain auth_token during authorization window
```python
from nanocontroller import get_token

get_token(
    ip address,     # Found on back of device, in app, or through network discovery tool 
    port            # Port defaults to "16021", but manual port discovery recommended. 
    )
```
    
---

## Getting Started

### Initializing the NanoController

```python
from nanocontroller import NanoController

nano = NanoController(
    auth_token="sdg7648t24ih"  # Obtained from "get_token"
    ip_address="172.20.7.17",  # Found on the back of the device, in the app, or via a network scan.
    port="16021",              # Default port is 16021. Discovery recommended.
    latitude=28.5383,          # Optional latitude, required for weather functions.
    longitude=-81.3792         # Optional longitude, required for weather functions.
)
```

or create a .env file 
```env
NANO_AUTH_TOKEN=
NANO_IP_ADDRESS=                # Strings
NANO_PORT=

NANO_LATITUDE =                 # Floats
NANO_LONGITUDE = 
```
and just
```python
from nano import NanoController

nano = NanoController()
```
Location can be updated at any point after initialization with:
```python
nano.set_location(lattitude, longitude)
```
---

## Methods

### General Controls

- **Get states:**
  ```python
  await nano.get_brightness()          # Get current brightness level.
  await nano.get_effect()              # Get the currently active effect.
  await nano.get_effects_list()        # List available effects downloaded in the app.
  await nano.get_state()               # Retrieve all states of the panels.
  ```

- **Set states:**
  ```python
  await nano.set_brightness(50)        # Set brightness (0-100).
  await nano.set_effect("Cocoa Beach")      # Set a specific effect by name.
  ```

---

### Custom Effects

Customize the panel colors and effects programmatically:

```python
await nano.custom(color_dict, loop=True)
```

- **Input Format:**
  ```python
  color_dict = {
      0: [(255, 0, 0, 10)],                     # Panel 1: Changes to Red with a 1-second transition.
      3: [(0, 255, 0, 10), (0, 0, 255, 30)],    # Panel 4: Changes to Green with a 1-second transition, then changes to blue with a 3 second transition. Loops by default, if Loop is False then remains static on blue after transitions
      ...
  }
  ```
  You can change all panels at once, or partial sets. The keys(0 to (number of panels - 1)) correspond to the set order of the panels. This defaults to "top_to_bottom" but can be changed with:
  ```python
  nano.panels.bottom_to_top()
  nano.panels.left_to_right()
  nano.panels.right_to_left()
  ```
  You can use multiple ordering methods when only one would leave room for ambiguity:
  ```python
  nano.panels.left_to_right()
  nano.panels.bottom_to_top()
  ```
  You can customize the ordering if the positions do not strictly follow a specific order:
  ```python
  print(nano.panels)                        # Gets IDs and relative postions        
  
  #Output: [Panel(id=30344, x=0, y=580), Panel(id=26383, x=0, y=464), Panel(id=19622, x=0, y=348), Panel(id=29596, x=0, y=232), Panel(id=11739, x=0, y=116), Panel(id=38168, x=0, y=0)]
  
  nano.panels.custom_sort(ordered_ids)      # ordered_ids is an array of the ids in a customized order, [26383, 19622, 30344, etc...]  

  ```
---

### Timer 

![Timer](nanocontroller/examples/IMG_2573.jpeg)

Gradually transition panels from one color to another, one by one, over a defined time. Follows the set ordering of panels, defaulting to "top_to_bottom". Accepts an optional function to execute at the end of the timer alongside the ending animation on the panels:

[Usage demonstration](https://drive.google.com/file/d/1lNFXadyBaEw3cxatC6kpN1qZ_msOE1W1/view?usp=sharing)

```python
await nano.timer(
    duration = 60,                  # Required - Time in seconds (≥ total number of panels).
    start_color = BLUE,             # Default blue.
    end_color = WHITE,              # Default white.
    alarm_length = 10,              # Alarm duration in seconds.
    alarm_brightness = 100,         # Full brightness for the alarm.
    end_animation = None,           # Custom `color_dict` for end effect. Defaults to quckly cycling through random colors.
    end_function = None,            # Optional async function to execute during end_animation
    end_function_kwargs = None      # Arguments for the end function.
)
```

[Application](https://drive.google.com/file/d/1lNFXadyBaEw3cxatC6kpN1qZ_msOE1W1/view?usp=sharing)

---

### Weather Visualization

1. **Set location:**
   ```python
   await nano.set_location(latitude, longitude)
   ```

2. **Display hourly forecast:**
   Each panel represents an hour. For example:
   - Heavy rain in 3 hours: Panel 3 quickly flashes blues and whites.
   - Overcast: Panel slowly transitions between grey tones.
   - weather_codes.py defines weather animations and can be customized. It is not fully optimized yet so edit it how you like.   

   ```python
   await nano.set_hourly_forecast(
       latitude = None, 
       longitude = None,                # If location has not been set at initialization or with .set_location() it must be provided here
       sunrise = 6,                     # Weather effects varry based on if they occur during day or night. Daytime hours fall within (sunrise, sunset) exclusive. 
       sunset = 18,
   )
   ```

3. **Display precipitation levels:**

   ![Precipitation](nanocontroller/examples/IMG_2566.jpeg)
    
   Sets the panels to display precipitaion level over "hour_interval" periods. Defaults to one hour per panel. Precipitation is represented on a gradient from the brightest blue for 100% chance and yellow for 0%. These colors are customizable. The image above represents (starting from the bottom): 0%, 30%, 60%, 100%, 90%, 25%.
   ```python
   await nano.set_precipitation(
            hour_interval = 1, 
            latitude = None,                  # Location necesarry if not already set
            longitude = None,
            max_color = BLUE,                 # Many standard colors are predefined
            min_color = YELLOW
    )
   ```

4. **Display temperature gradients:**

   ![Temperature](nanocontroller/examples/IMG_2550.jpeg)

   Sets the panels to display the temperature per hour intervals. Defaults to one hour per panel.
    Default color gradients defined by the dictionary:
    ```python
    gradient_dict = {
        0: {
            "start": (255, 255, 255),  # Bright white
            "end": (255, 255, 255)     # Bright white
        },
        40: {
            "start": (255, 255, 255),  # Bright white
            "end": (128, 128, 128)     # Light white
        },
        50: {
            "start": (90, 0, 140),    # darker purple
            "end": (150, 50, 255)      # purple
        },
        60: {
            "start": (0, 0, 255),      # Blue
            "end": (40, 90, 255)       # Slightly lighter blue
        },
        70: {
            "start": (0, 255, 0),      # Green
            "end": (90, 255, 60)       # Yellowish green
        },
        80: {
            "start": (255, 255, 0),    # Yellow
            "end": (255, 0, 0)         # Red
        },
        100: {
            "start": (255, 0, 0),      # Red
            "end": (255, 0, 0)         # Red
        }
    }
    ```
    Custom gradient dictionary of the same form can be passed to accomadate different climates. Intervals can be customized. "start" defines the color at the lowest point in the interval and "end" defines the color at the highest point in the interval. 


    ```python
    await nano.set_temperature(
            hour_interval = 1,       
            latitude = None, 
            longitude = None, 
            gradient_dict = None,
    )
    ```

---

## Features

### Built-in Functionalities
- **Weather visualization:** Displays hourly forecasts, precipitation, and temperature using panel colors.
- **Timers:** Create visual countdowns with customizable colors and alarms.

### Extendability
Leverage the `nano.custom()` method to:
- Display dynamic notifications.
- Create personalized status displays.

---
## Contributing

Feel free to submit issues or pull requests on the [GitHub repository](https://github.com/your-repo/nanocontroller). Contributions to add new features or improve existing ones are always welcome.

---

## License

This package is licensed under the MIT License. See the LICENSE file for more information.