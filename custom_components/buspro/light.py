"""
This component provides light support for Buspro.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/...
"""

import logging
import time
import asyncio

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.light import (
    LightEntity, 
    ColorMode, 
    PLATFORM_SCHEMA, 
    ATTR_BRIGHTNESS
)
from homeassistant.const import (CONF_NAME, CONF_DEVICES)
from homeassistant.core import callback

from ..buspro import DATA_BUSPRO
from datetime import timedelta
import homeassistant.helpers.event as event


_LOGGER = logging.getLogger(__name__)

DEFAULT_DEVICE_RUNNING_TIME = 0
DEFAULT_PLATFORM_RUNNING_TIME = 0
DEFAULT_DIMMABLE = True

DEVICE_SCHEMA = vol.Schema({
    vol.Optional("running_time", default=DEFAULT_DEVICE_RUNNING_TIME): cv.positive_int,
    vol.Optional("dimmable", default=DEFAULT_DIMMABLE): cv.boolean,
    vol.Required(CONF_NAME): cv.string,
})

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional("running_time", default=DEFAULT_PLATFORM_RUNNING_TIME): cv.positive_int,
    vol.Required(CONF_DEVICES): {cv.string: DEVICE_SCHEMA},
})


# noinspection PyUnusedLocal
async def async_setup_platform(hass, config, async_add_entites, discovery_info=None):
    """Set up Buspro light devices."""
    # noinspection PyUnresolvedReferences
    from .pybuspro.devices import Light

    hdl = hass.data[DATA_BUSPRO].hdl
    devices = []
    platform_running_time = int(config["running_time"])

    for address, device_config in config[CONF_DEVICES].items():
        name = device_config[CONF_NAME]
        device_running_time = int(device_config["running_time"])
        dimmable = bool(device_config["dimmable"])

        if device_running_time == 0:
            device_running_time = platform_running_time
        if dimmable:
            device_running_time = 0

        address2 = address.split('.')
        device_address = (int(address2[0]), int(address2[1]))
        channel_number = int(address2[2])
        _LOGGER.debug("Adding light '{}' with address {} and channel number {}".format(name, device_address, channel_number))

        light = Light(hdl, device_address, channel_number, name)
        devices.append(BusproLight(hass, light, device_running_time, dimmable))

    async_add_entites(devices)
    for device in devices:
        await device.async_read_status()


# noinspection PyAbstractClass
class BusproLight(LightEntity):
    """Representation of a Buspro light."""

    def __init__(self, hass, device, running_time, dimmable):
        self._hass = hass
        self._device = device
        self._running_time = running_time
        self._dimmable = dimmable
        
        # <--- OPTIMISTIC MODE: Initialize the override variable
        self._optimistic_brightness = None 
        self._optimistic_timeout = 0

        # <--- DEBOUNCE/HYSTERESIS STATE
        self._debounced_is_on = None
        self._debounced_brightness = 0
        self._debounce_task = None

        if self._dimmable:
            self._attr_color_mode = ColorMode.BRIGHTNESS
            self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}
        else:
            self._attr_color_mode = ColorMode.ONOFF
            self._attr_supported_color_modes = {ColorMode.ONOFF}
        self.async_register_callbacks()
         # Set the polling interval (e.g., every 60 minutes)
        self._polling_interval = timedelta(minutes=60)
        event.async_track_time_interval(hass, self.async_update, self._polling_interval)


    @callback
    def async_register_callbacks(self):
        """Register callbacks to update hass after device was changed."""

        async def after_update_callback(device):
            """Call after device was updated."""
            hardware_is_on = device.is_on
            hardware_brightness = (device.current_brightness / 100 * 255) if device.current_brightness is not None else 0
            _LOGGER.debug(f"DEBUG_BUSPRO_LIGHT_CB: {self.name} callback: hardware_is_on={hardware_is_on}, hardware_brightness={hardware_brightness}, current_debounced={self._debounced_is_on}")
            
            # Initialize debounced state on first read - write state once
            if self._debounced_is_on is None:
                self._debounced_is_on = hardware_is_on
                self._debounced_brightness = hardware_brightness
                self.async_write_ha_state()
                return

            # Check if optimistic mode has expired
            if self._optimistic_brightness is not None:
                if time.time() > self._optimistic_timeout:
                    self._optimistic_brightness = None

            # Asymmetric hysteresis debounce:
            #   ON transitions:  2s delay  (light appears quickly when turned on)
            #   OFF transitions: 20s delay (prevents PIR-triggered lights from flickering
            #                               out of the active list when sensors re-trigger)
            # User-initiated on/off bypass this entirely via optimistic state in async_turn_on/off.
            DEBOUNCE_ON_SECS  = 4.0
            DEBOUNCE_OFF_SECS = 4.0

            if hardware_is_on == self._debounced_is_on:
                # Hardware confirmed current stable state ? cancel any pending reversal
                if self._debounce_task is not None:
                    self._debounce_task.cancel()
                    self._debounce_task = None
                # Update brightness immediately if it changed while staying ON
                if hardware_is_on and hardware_brightness != self._debounced_brightness:
                    self._debounced_brightness = hardware_brightness
                    if self._optimistic_brightness is None:
                        self.async_write_ha_state()
            else:
                # Hardware disagrees ? start/reset debounce timer
                # Always cancel + restart so repeated flaps extend the window
                if self._debounce_task is not None:
                    self._debounce_task.cancel()
                    self._debounce_task = None

                delay = DEBOUNCE_ON_SECS if hardware_is_on else DEBOUNCE_OFF_SECS

                async def _do_debounce(target_on, target_bright, wait):
                    try:
                        await asyncio.sleep(wait)
                        prev_is_on = self._debounced_is_on
                        prev_brightness = self._debounced_brightness
                        self._debounced_is_on = target_on
                        self._debounced_brightness = target_bright if target_on else 0
                        self._debounce_task = None
                        # Only write state if something actually changed
                        if self._debounced_is_on != prev_is_on or self._debounced_brightness != prev_brightness:
                            if self._optimistic_brightness is None:
                                self.async_write_ha_state()
                    except asyncio.CancelledError:
                        pass

                self._debounce_task = self.hass.async_create_task(
                    _do_debounce(hardware_is_on, hardware_brightness, delay)
                )
            # NOTE: Do NOT call async_write_ha_state() unconditionally here.
            # State is written only when the debounced value actually changes.


        self._device.register_device_updated_cb(after_update_callback)

    @property
    def should_poll(self):
        """No polling needed within Buspro."""
        return True # Changed to True to keep Google Assistant 'online' and sync state.

    async def async_update(self, *args):
        """Fetch new state data for this light asynchronously."""
        await self.async_read_status()

    @property
    def name(self):
        """Return the display name of this light."""
        return self._device.name

    @property
    def available(self):
        """Return True if entity is available."""
        return self._hass.data[DATA_BUSPRO].connected

    @property
    def brightness(self):
        """Return the brightness of the light."""
        # 1. OPTIMISTIC MODE: Return fake brightness if pending
        if self._optimistic_brightness is not None:
            if time.time() > self._optimistic_timeout:
                self._optimistic_brightness = None
            else:
                return self._optimistic_brightness

        # 2. DEBOUNCE MODE: Return last stable hardware state
        if self._debounced_is_on is not None:
            return self._debounced_brightness

        # Standard Logic
        if self._device.current_brightness is None:
            return 0
        brightness = self._device.current_brightness / 100 * 255
        return brightness

    @property
    def is_on(self):
        """Return true if light is on."""
        # 1. OPTIMISTIC MODE: Return fake state if pending
        if self._optimistic_brightness is not None:
            if time.time() > self._optimistic_timeout:
                self._optimistic_brightness = None
            else:
                return self._optimistic_brightness > 0
            
        # 2. DEBOUNCE MODE: Return last stable hardware state
        if self._debounced_is_on is not None:
            return self._debounced_is_on

        return self._device.is_on

    async def async_turn_on(self, **kwargs):
        """Instruct the light to turn on."""
        target_ha_brightness = kwargs.get(ATTR_BRIGHTNESS, 255)
        hdl_brightness = int(target_ha_brightness / 255 * 100)

        if not self.is_on and self._device.previous_brightness is not None and hdl_brightness == 100:
            hdl_brightness = self._device.previous_brightness
            target_ha_brightness = int(hdl_brightness / 100 * 255)

        # Cancel any pending debounce task instantly
        if self._debounce_task is not None:
            self._debounce_task.cancel()
            self._debounce_task = None
        self._debounced_is_on = True
        self._debounced_brightness = target_ha_brightness

        # 1. Update HA instantly so Google Home sees the change immediately
        self._optimistic_brightness = target_ha_brightness
        self._optimistic_timeout = time.time() + self._running_time + 4.0
        self.async_write_ha_state()

        # 2. Send command to HDL and await it so Google Assistant knows it's sent
        await self._device.set_brightness(hdl_brightness, self._running_time)
        
        # 3. If fading, schedule a status read after it completes
        if self._running_time > 0:
            async def _update_after_fade():
                await asyncio.sleep(self._running_time + 1.5)
                await self._device.read_status()
            self.hass.async_create_task(_update_after_fade())

    async def async_turn_off(self, **kwargs):
        """Instruct the light to turn off."""
        # Cancel any pending debounce task instantly
        if self._debounce_task is not None:
            self._debounce_task.cancel()
            self._debounce_task = None
        self._debounced_is_on = False
        self._debounced_brightness = 0

        # 1. Update HA instantly so Google Home sees the change immediately
        self._optimistic_brightness = 0
        self._optimistic_timeout = time.time() + self._running_time + 4.0
        self.async_write_ha_state()

        # 2. Send command to HDL and await it so Google Assistant knows it's sent
        await self._device.set_off(self._running_time)

        # 3. If fading, schedule a status read after it completes
        if self._running_time > 0:
            async def _update_after_fade():
                await asyncio.sleep(self._running_time + 1.5)
                await self._device.read_status()
            self.hass.async_create_task(_update_after_fade())
    @property
    def unique_id(self):
        """Return the unique id."""
        return self._device.device_identifier

    async def async_read_status(self):
        """Read the status of the device."""
        await self._device.read_status()
        self.async_write_ha_state()
