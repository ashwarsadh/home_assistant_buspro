"""
This component provides cover support for Buspro.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/...
"""

import logging

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.cover import CoverEntity, CoverEntityFeature, CoverDeviceClass, PLATFORM_SCHEMA, ATTR_POSITION
from homeassistant.const import (CONF_NAME, CONF_DEVICES)
from homeassistant.core import callback

from ..buspro import DATA_BUSPRO
from datetime import timedelta
import homeassistant.helpers.event as event
_LOGGER = logging.getLogger(__name__)
DEFAULT_OPENING_TIME = 20
DEFAULT_ADJUSTABLE = True
_adjustable=True

DEVICE_SCHEMA = vol.Schema({
    vol.Required(CONF_NAME): cv.string,
    vol.Optional("opening_time", default=DEFAULT_OPENING_TIME): cv.positive_int,
    vol.Optional("adjustable", default=DEFAULT_ADJUSTABLE): cv.boolean,    
})

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_DEVICES): {cv.string: DEVICE_SCHEMA},

})


# noinspection PyUnusedLocal
async def async_setup_platform(hass, config, async_add_entites, discovery_info=None):
    """Set up Buspro cover devices."""
    # noinspection PyUnresolvedReferences
    from .pybuspro.devices import Cover

    hdl = hass.data[DATA_BUSPRO].hdl
    devices = []

    for address, device_config in config[CONF_DEVICES].items():
        name = device_config[CONF_NAME]
        opening_time=int(device_config["opening_time"])
        _adjustable=bool(device_config["adjustable"])

        address2 = address.split('.')
        device_address = (int(address2[0]), int(address2[1]))
        channel_number = int(address2[2])
        _LOGGER.debug("Adding cover '{}' with address {} and channel number {} and is adjustable {}".format(name, device_address,
                                                                                        channel_number, _adjustable))

        cover = Cover(hdl, device_address, channel_number, name, )

        devices.append(BusproCover(hass, cover))

    async_add_entites(devices)
        # Read status of all devices on startup
    for device in devices:
        await device.async_update()


# noinspection PyAbstractClass
class BusproCover(CoverEntity):
    """Representation of a Buspro cover."""

    def __init__(self, hass, device):
        self._hass = hass
        self._device = device
        self._attr_device_class = CoverDeviceClass.CURTAIN
        # self.setup_features()
        self.async_register_callbacks()
                 # Set the polling interval (e.g., every 30 seconds)
        self._polling_interval = timedelta(minutes=60)
        event.async_track_time_interval(hass, self.async_update, self._polling_interval)

    @callback
    def async_register_callbacks(self):
        """Register callbacks to update hass after device was changed."""

        # noinspection PyUnusedLocal
        async def after_update_callback(device):
            """Call after device was updated."""
            self.async_write_ha_state()

        self._device.register_device_updated_cb(after_update_callback)

    @property
    def should_poll(self):
        """No polling needed within Buspro."""
        return True

    @property
    def name(self):
        """Return the display name of this cover."""
        return self._device.name

    @property
    def available(self):
        """Return True if entity is available."""
        return self._hass.data[DATA_BUSPRO].connected

    @property
    def is_closed(self):
        """Return true if cover is closed."""
        return self._device.is_closed

    @property
    def is_closing(self):
        """Return true if cover is closing for 30 seconds after command."""
        return self._device.is_closing

    @property
    def is_opening(self):
        """Return true if cover is opening for 30 seconds after command."""
        return self._device.is_opening
        
    @property
    def current_cover_position(self):
        """Return true if cover is opening for 30 seconds after command."""
        return self._device.current_cover_position
    

    # def setup_features(self):
    #     """Return the list of supported features."""
    #     self._attr_supported_features = (   CoverEntityFeature.OPEN |
    #                                         CoverEntityFeature.CLOSE |
    #                                         CoverEntityFeature.STOP)

    @property
    def supported_features(self) -> CoverEntityFeature:
        """Flag supported features."""
        if _adjustable:
            features = (
                CoverEntityFeature.OPEN
                | CoverEntityFeature.CLOSE
                | CoverEntityFeature.STOP
                | CoverEntityFeature.SET_POSITION
            )
        else:
                features = (
                CoverEntityFeature.OPEN
                | CoverEntityFeature.CLOSE
                | CoverEntityFeature.STOP
            )
        return features

    async def async_open_cover(self, **kwargs):
        """Instruct the cover to open."""
        await self._device.set_open()

    async def async_close_cover(self, **kwargs):
        """Instruct the cover to close."""
        await self._device.set_close()


    async def async_stop_cover(self, **kwargs):
        """Instruct the cover to stop."""
        await self._device.set_stop()

    async def async_read_status(self):
        """Read the status of the device."""
        status = self._device._status
        if status == None:
            """Fetch new state data for this light."""
            await self._device.read_status()
        self.async_write_ha_state()
    
    async def async_update(self, *args):
        """Fetch new state data for this light."""
        await self.async_read_status()

#    async def async_update(self):
 #       """Fetch new state data for this light."""
  #      await self.async_read_status()
    
    async def async_set_cover_position(self, **kwargs):
        position = int(kwargs.get(ATTR_POSITION))
        await self._device.set_position(position)

    @property
    def unique_id(self):
        """Return the unique id."""
        return self._device.device_identifier
        
