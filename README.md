# HDL Buspro

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

The HDL Buspro integration allows you to control your HDL Buspro system from Home Assistant.

## Installation
Under HACS -> Integrations, add custom repository "https://github.com/eyesoft/home_assistant_buspro/" with Category "Integration". Select the integration named "HDL Buspro" and download it.

Restart Home Assistant.

Go to Settings > Integrations and Add Integration "HDL Buspro". Type in IP address and port number of the gateway.

## Configuration

#### Light platform
   
To use your Buspro light in your installation, add the following to your configuration.yaml file: 

```yaml
light:
  - platform: buspro
    running_time: 3
    devices:
      1.89.1:
        name: Living Room Light
        running_time: 5
      1.89.2:
        name: Front Door Light
        dimmable: False
```
+ **running_time** _(int) (Optional)_: Default running time in seconds for all devices. Running time is 0 seconds if not set.
+ **devices** _(Required)_: A list of devices to set up
  + **X.X.X** _(Required)_: The address of the device on the format `<subnet ID>.<device ID>.<channel number>`
    + **name** _(string) (Required)_: The name of the device
    + **running_time** _(int) (Optional)_: The running time in seconds for the device. If omitted, the default running time for all devices is used.
    + **dimmable** _(boolean) (Optional)_: Is the device dimmable? Default is True. 

#### Switch platform

To use your Buspro switch in your installation, add the following to your configuration.yaml file: 

```yaml
switch:
  - platform: buspro
    devices:
      1.89.1:
        name: Living Room Switch
      1.89.2:
        name: Front Door Switch
```
+ **devices** _(Required)_: A list of devices to set up
  + **X.X.X** _(Required)_: The address of the device on the format `<subnet ID>.<device ID>.<channel number>`
    + **name** _(string) (Required)_: The name of the device

#### Fan platform
   
To use your Buspro Fan in your installation,same as light, but shows as Fan in HA UI and Google Assitant, allowing better controls and grouping.
Add the following to your configuration.yaml file: 

```yaml
fan:
  - platform: buspro
    running_time: 3
    devices:
      1.89.1:
        name: Living Room Light
        running_time: 5
      1.89.2:
        name: Front Door Light
        dimmable: False
```
+ **running_time** _(int) (Optional)_: Default running time in seconds for all devices. Running time is 0 seconds if not set.
+ **devices** _(Required)_: A list of devices to set up
  + **X.X.X** _(Required)_: The address of the device on the format `<subnet ID>.<device ID>.<channel number>`
    + **name** _(string) (Required)_: The name of the device
    + **running_time** _(int) (Optional)_: The running time in seconds for the device. If omitted, the default running time for all devices is used.
    + **dimmable** _(boolean) (Optional)_: Is the device dimmable? Default is True. 


#### Sensor platform

To use your Buspro sensor in your installation, add the following to your configuration.yaml file: 

```yaml
sensor:
  - platform: buspro
    devices:
      - address: 1.74
        name: Living Room
        type: temperature
        unit_of_measurement: °C
        device_class: temperature
        device: dlp
      - address: 1.74
        name: Front Door
        type: illuminance
        unit_of_measurement: lux
```
+ **devices** _(Required)_: A list of devices to set up
  + **address** _(string) (Required)_: The address of the sensor device on the format `<subnet ID>.<device ID>`
  + **name** _(string) (Required)_: The name of the device
  + **type** _(string) (Required)_: Type of sensor to monitor. 
    + Available sensors: 
     + temperature
     + illuminance
  + **unit_of_measurement** _(string) (Optional)_: text to be displayed as unit of measurement
  + **device_class** _(string) (Optional)_: HASS device class e.g., "temperature" 
  (https://www.home-assistant.io/components/sensor/)
  + **device** _(string) (Optional)_: The type of sensor device:
    + dlp 


#### Binary sensor platform

To use your Buspro binary sensor in your installation, add the following to your configuration.yaml file: 

```yaml
binary_sensor:
  - platform: buspro
    devices:
      - address: 1.74
        name: Living Room
        type: motion
        device_class: motion
      - address: 1.74.100
        name: Front Door
        type: universal_switch
      - address: 1.75.3
        name: Kitchen switch
        type: single_channel
        device: pir
```
+ **devices** _(Required)_: A list of devices to set up
  + **address** _(string) (Required)_: The address of the sensor device on the format `<subnet ID>.<device ID>`. If 
  'type' = 'universal_switch' universal switch number must be appended to the address. 
  + **name** _(string) (Required)_: The name of the device
  + **type** _(string) (Required)_: Type of sensor to monitor. 
    + Available sensors: 
      + motion 
      + dry_contact_1 
      + dry_contact_2
      + universal_switch
      + single_channel
  + **device_class** _(string) (Optional)_: HASS device class e.g., "motion" 
  (https://www.home-assistant.io/components/binary_sensor/)
   + **device** _(string) (Optional)_: The type of sensor device:
    + pir
    + 8in1
    + 12in1

Older Devices like CMS-PIR are supported via PIR

#### Climate platform

To use your Buspro panel climate control in your installation, add the following to your configuration.yaml file: 

Added Support for AC Control via DLP Panel command, we need to mention Subnet and Device ID of Room DLP Panel which can be used to control  the AC.
I have removed Floor Heating and Heating Modes for my needs, but someone requiring Floor heating instead of Air Conditioner use climate.py from Original Repo or merge both to and create an option for panel type as floor heater and ac and also mention option to provide their supported modes like cooling and heating.


```yaml
climate:
  - platform: buspro
    devices:
      - address: 1.74
        name: Living Room
      - address: 1.74
        name: Front Door
```
+ **devices** _(Required)_: A list of devices to set up
  + **address** _(string) (Required)_: The address of the sensor device on the format `<subnet ID>.<device ID>`
  + **name** _(string) (Required)_: The name of the device
    

---
## Services

#### Sending an arbitrary message:
```
Domain: buspro
Service: send_message
Service Data: {"address": [1,74], "operate_code": [4,78], "payload": [1,100,0,3]}
```
#### Activating a scene:
```
Domain: buspro
Service: activate_scene
Service Data: {"address": [1,74], "scene_address": [3,5]}
```
#### Setting an universal switch:
```
Domain: buspro
Service: set_universal_switch
Service Data: {"address": [1,74], "switch_number": 100, "status": 1}
```

#### List of Changes in this Fork:

## General Changes:
I have updated polling / status update on HA startup for all devices, so all devices start showing available.
I have also fixed update process on various devices to report correct device status

## Device wise Change List : 
# Binary sensor:

Added additional option 
device: 

with options 
8in1
12in1
pir
Older devices like PIR do not respond to request sensor status, but newer devices do, so we can set our device type
Added additional BusPro code to check status of CMS-PIR Motion Sensors

# sensor:
Fixed temperature variance of 20 degree on certain devices and more frequent reporting of current temperature status.

# climate :

Added Support for AC Control via DLP Panel command, we need to mention Subnet and Device ID of Room DLP Panel which can be used to control  the AC.
I have removed Floor Heating and Heating Modes for my needs, but someone can merge both climate.py and create an option for panel type as floor heater and ac and also mention option to provide their supported modes like cooling and heating.

# cover :

I have added Extensive Curtain support forked from IlPicasso (https://github.com/IlPicasso/home_assistant_buspro) 
additional option :
opening_time : in seconds (default 20)
adjustable : True or False (default True)

Made Curtain supported on Google Assistant.
Made Curtain Adjustable to specific position and also report current position.
You need to check on stopwatch how many seconds it takes to open a particular curtain and mention that time in opening_time (set as 20s by default)
Based on it, it will calculate current position while opening and closing
When Curtain Position is set in between open and close then it will first close the curtain , so we can be sure that status of curtain is synced with the HA as there is no way in BusPro to know current status of curtain, then it will open the curtain to desired position.
All is based on time, so to open Curtain at 50% it will take 30 seconds if opening time is 20s, 
20 seconds to completely close it, whatever condition it is in and 10s to open it to 50

It keeps curtain position reported at 99% or 1% so both open and close button remain active, so in case position is not matching with buspro you can still operate the button and it doesnt get greyed out.

# Added additional device FAN

configuration is same as light with optional dimmable which can be set to false if Fan speed cannot be set.

This shows Fan seperately on Google Home and HA, so they are not confused with lights

# Light:
non dimmable lights were reporting as dimmable to HA, fixed this bug
Fixed current status getting updated on HA  

