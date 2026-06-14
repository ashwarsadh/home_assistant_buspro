# HDL Buspro Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

The **HDL Buspro** custom integration allows you to control and monitor your HDL Buspro / SmartBus home automation system from Home Assistant.

---

## Features

- **Light Platform**: Dimmable and non-dimmable light controls with symmetric 4.0-second state debouncing and optimistic state synchronization to prevent flickering.
- **Fan Platform**: Dimmable and non-dimmable fan controls, exposed correctly as Fans in Home Assistant and Google Assistant.
- **Switch Platform**: Relays and binary switches.
- **Cover Platform**: Time-based curtain and blind support with position feedback.
- **Climate Platform**:
  - **AC Control**: Control Air Conditioning units via DLP panel commands.
  - **Floor Heating**: Modern support for HDL Floor Heating modules (e.g., `HDL-MFH06.432`) utilizing both legacy and float-based protocols.
- **Sensors**: Temperature and illuminance (lux) readings from HDL sensors, with automatic temperature offset correction.
- **Binary Sensors**: Motion detection and Dry Contacts (e.g., `sb-dry-4z`) with automatic query type detection.

---

## Installation

1. Open **HACS** (Home Assistant Community Store) in your Home Assistant panel.
2. Go to **Integrations**, click the three dots in the top-right corner, and select **Custom repositories**.
3. Add the URL of your repository: `https://github.com/ashwarsadh/home_assistant_buspro/` with the category **Integration**.
4. Click **Download** on the newly added "HDL Buspro" integration.
5. Restart Home Assistant.
6. Navigate to **Settings > Devices & Services**, click **Add Integration**, search for **HDL Buspro**, and enter the IP gateway address and port number.

---

## Configuration

Add the platforms you wish to integrate into your `configuration.yaml`:

### Light Platform
```yaml
light:
  - platform: buspro
    running_time: 3
    devices:
      1.89.1:
        name: "Living Room Light"
        running_time: 5
      1.89.2:
        name: "Front Door Light"
        dimmable: false
```
* **running_time** *(int) (Optional)*: Default running time in seconds.
* **dimmable** *(boolean) (Optional)*: Set to `false` for non-dimmable/binary lights.

---

### Switch Platform
```yaml
switch:
  - platform: buspro
    devices:
      1.89.1:
        name: "Living Room Switch"
```

---

### Fan Platform
```yaml
fan:
  - platform: buspro
    devices:
      100.13.1:
        name: "Kitchen Exhaust Fan"
        dimmable: true
```

---

### Cover Platform
```yaml
cover:
  - platform: buspro
    devices:
      100.221.1:
        name: "Living Room Curtains"
        opening_time: 20
```
* **opening_time** *(int) (Optional)*: The time in seconds it takes to completely open the curtain (used to calculate positioning).

---

### Climate Platform

Supports both **Air Conditioners** (using DLP panels) and **Floor Heating** controllers.

```yaml
climate:
  - platform: buspro
    devices:
      # Air Conditioner via DLP Panel (defaults to type: ac)
      - address: 100.154
        name: "2nd Living Room AC"
        type: ac
        preset_modes:
          - away
          - home
          - sleep

      # Floor Heating Module Channel (e.g., bath, living room)
      - address: 100.207
        name: "Bath Floor Heating"
        type: floor_heating
        channel: 1
        preset_modes:
          - home
          - sleep
          - away
```
* **type** *(string) (Optional)*: Either `ac` or `floor_heating`. Defaults to `ac`.
* **channel** *(int) (Optional)*: The channel on the floor heating module (1–6). Required for `floor_heating`.
* **preset_modes** *(list) (Optional)*: Supported presets like `home` (Day), `sleep` (Night), `away` (Away).

---

### Sensor Platform
```yaml
sensor:
  - platform: buspro
    devices:
      - address: 100.173
        name: "Living Room Temp"
        type: temperature
        device: 8in1
      - address: 100.173
        name: "Living Room Lux"
        type: illuminance
```
* **device** *(string) (Optional)*: Specify `8in1` or `12in1` to automatically subtract the `20` degree temperature offset used in raw HDL sensor status packets.

---

### Binary Sensor Platform (Motion & Dry Contacts)

Specifically optimized for dry contact modules such as the `sb-dry-4z`.

```yaml
binary_sensor:
  - platform: buspro
    devices:
      # 8in1 Motion Sensor
      - address: 100.173
        name: "Living Room Motion"
        type: motion
        device_class: motion

      # Dry Contact Sensors (e.g., sb-dry-4z at subnet 100, device 91)
      - address: 100.91.1
        name: "Living Room Window"
        type: dry_contact
        device_class: window
      - address: 100.91.2
        name: "Front Room Window"
        type: dry_contact
        device_class: window
      - address: 100.91.3
        name: "Terrace Door"
        type: dry_contact
        device_class: door
      - address: 100.91.4
        name: "Parking Gate"
        type: dry_contact
        device_class: garage_door
```
* **type** *(string) (Required)*: Set to `motion`, `universal_switch`, `single_channel`, or `dry_contact`.
* **device_class** *(string) (Optional)*: The Home Assistant device class (e.g., `window`, `door`, `garage_door`, `motion`).

---

## Services

This integration exposes standard services to allow custom scripts and automation to send raw commands onto your HDL network.

### Sending an Arbitrary Message
```yaml
service: buspro.send_message
data:
  address: [1, 74]
  operate_code: [4, 78]
  payload: [1, 100, 0, 3]
```

### Activating a Scene
```yaml
service: buspro.activate_scene
data:
  address: [1, 74]
  scene_address: [3, 5]
```

### Setting a Universal Switch
```yaml
service: buspro.set_universal_switch
data:
  address: [1, 74]
  switch_number: 100
  status: 1
```

---

## License

This project is licensed under the MIT License.
