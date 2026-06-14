import asyncio
import struct

from .control import (
    _ReadPanelAC,
    _ControlPanelAC,
    _ReadFloorHeatingStatusNew,
    _ControlFloorHeatingStatusNew,
    _ReadFloorHeatingTemperatureNew,
    _ReadFloorHeatingTemperatureLegacy,
)
from .device import Device
from ..helpers.enums import *
from ..helpers.generics import Generics


class ControlPanelAC:
    def __init__(self):
        self.status = None
        self.mode = None
        self.normal_temperature = None
        

class Climate(Device):
    def __init__(self, buspro, device_address, name=""):
        super().__init__(buspro, device_address, name)

        self._buspro = buspro
        self._device_address = device_address
        self._status = None             # On/Off
        self._mode= None
        self._current_temperature = None
        self._normal_temperature = None
        
        self.register_telegram_received_cb(self._telegram_received_cb)
        self._call_read_current_panel_status(run_from_init=True)
        self._call_read_current_panel_temp(run_from_init=True)

    def _telegram_received_cb(self, telegram):
        if telegram.operate_code == OperateCode.ReadPanelACResponse:
            if telegram.payload[0]==3:
                self._status = telegram.payload[1]
                self._mode = telegram.payload[1]
                self._call_device_updated()
            elif telegram.payload[0]==4:
                self._current_temperature = telegram.payload[1]
                self._normal_temperature = telegram.payload[1]
                self._call_device_updated()

        elif telegram.operate_code == OperateCode.ControlPanelACResponse:
            if telegram.payload[0]==3:
                self._status = telegram.payload[1]
                self._mode = telegram.payload[1]
                self._call_device_updated()
            elif telegram.payload[0]==4:
                self._current_temperature = telegram.payload[1]
                self._normal_temperature = telegram.payload[1]
                self._call_device_updated()

        elif telegram.operate_code == OperateCode.BroadcastTemperatureResponse:
            # channel_number = telegram.payload[0]
            self._current_temperature = telegram.payload[1]
            self._call_device_updated()

    async def read_status(self):
        rfhs = _ReadPanelAC(self._buspro)
        rfhs.subnet_id, rfhs.device_id = self._device_address
        rfhs.command=3 #read status on off
        await rfhs.send()

    async def read_temperature(self):
        rfhs = _ReadPanelAC(self._buspro)
        rfhs.subnet_id, rfhs.device_id = self._device_address
        rfhs.command=4 #read temperature
        await rfhs.send()

    def _telegram_received_control_ac_status_cb(self, telegram, panel_status):

        if telegram.operate_code == OperateCode.ReadPanelACResponse:
            self.unregister_telegram_received_cb(
                self._telegram_received_control_ac_status_cb, panel_status)
            if telegram.payload[0]==3:
                self._status = telegram.payload[1]
                self._mode = telegram.payload[1]
            elif telegram.payload[0]==4:
                self._current_temperature = telegram.payload[1]
                self._normal_temperature = telegram.payload[1]

        
            if hasattr(panel_status, 'status'):
                if panel_status.status is not None:
                    status = panel_status.status
                    mode = panel_status.status
                    command = 3
            if hasattr(panel_status, 'mode'):
                if panel_status.mode is not None:
                    mode = panel_status.mode
                    status=panel_status.mode
                    command = 3
            normal_temperature=None
            _current_temperature=None
            if hasattr(panel_status, 'normal_temperature'):
                if panel_status.normal_temperature is not None:
                    normal_temperature = panel_status.normal_temperature
                    command = 4
            if hasattr(panel_status, '_current_temperature'):
                if panel_status._current_temperature is not None:
                    _current_temperature = panel_status._current_temperature
                    command = 4
            if normal_temperature is None:
                normal_temperature=_current_temperature

            if mode is None:
                mode=normal_temperature

            cfhs_ = _ControlPanelAC(self._buspro)
            cfhs_.subnet_id, cfhs_.device_id = self._device_address
            cfhs_.command = command
            cfhs_.mode = mode

            async def send_control_panel_status(cfhs__):
                await cfhs__.send()

            asyncio.ensure_future(send_control_panel_status(cfhs_), loop=self._buspro.loop)

    async def control_ac_temperature(self, panel_status: ControlPanelAC):
        self.register_telegram_received_cb(self._telegram_received_control_ac_status_cb, panel_status)
        rfhs = _ControlPanelAC(self._buspro)
        rfhs.subnet_id, rfhs.device_id = self._device_address
        rfhs.command=4
        normal_temperature=None
        _current_temperature=None
        mode=None
        status=None
        if hasattr(panel_status, 'status'):
            if panel_status.status is not None:
                status = panel_status.status
                mode = panel_status.status
                command = 3
        if hasattr(panel_status, 'mode'):
            if panel_status.mode is not None:
                mode = panel_status.mode
                status=panel_status.mode
                command = 3
        if hasattr(panel_status, 'normal_temperature'):
            if panel_status.normal_temperature is not None:
                normal_temperature = panel_status.normal_temperature
                command = 4
        if hasattr(panel_status, '_current_temperature'):
            if panel_status._current_temperature is not None:
                _current_temperature = panel_status._current_temperature
                command = 4
        if normal_temperature is None:
            normal_temperature=_current_temperature

        if mode is None:
            mode=normal_temperature
        rfhs.mode=mode
        await rfhs.send()

    async def control_ac_status(self, panel_status: ControlPanelAC):
        self.register_telegram_received_cb(self._telegram_received_control_ac_status_cb, panel_status)
        rfhs = _ControlPanelAC(self._buspro)
        rfhs.subnet_id, rfhs.device_id = self._device_address
        rfhs.command=3
        normal_temperature=None
        _current_temperature=None
        if hasattr(panel_status, 'status'):
            if panel_status.status is not None:
                status = panel_status.status
                mode = panel_status.status
                command = 3
        if hasattr(panel_status, 'mode'):
            if panel_status.mode is not None:
                mode = panel_status.mode
                status=panel_status.mode
                command = 3
        if hasattr(panel_status, 'normal_temperature'):
            if panel_status.normal_temperature is not None:
                normal_temperature = panel_status.normal_temperature
                command = 4
        if hasattr(panel_status, '_current_temperature'):
            if panel_status._current_temperature is not None:
                _current_temperature = panel_status._current_temperature
                command = 4
        if normal_temperature is None:
            normal_temperature=_current_temperature

        if mode is None:
            mode=normal_temperature
        rfhs.mode=mode
        await rfhs.send()

    def _call_read_current_panel_status(self, run_from_init=False):

        async def read_current_panel_status():
            if run_from_init:
                await asyncio.sleep(5)

            rfhs = _ReadPanelAC(self._buspro)
            rfhs.subnet_id, rfhs.device_id = self._device_address
            rfhs.command=3
            await rfhs.send()

        asyncio.ensure_future(read_current_panel_status(), loop=self._buspro.loop)
    def _call_read_current_panel_temp(self, run_from_init=False):

        async def read_current_panel_temp():
            if run_from_init:
                await asyncio.sleep(5)

            rfhs = _ReadPanelAC(self._buspro)
            rfhs.subnet_id, rfhs.device_id = self._device_address
            rfhs.command=4
            await rfhs.send()

        asyncio.ensure_future(read_current_panel_temp(), loop=self._buspro.loop)
    @property
    def unit_of_measurement(self):
        generics = Generics()
        return generics.get_enum_value(TemperatureType, 0)

    @property
    def is_on(self):
        if self._status == 1:
            return True
        else:
            return False

    @property
    def mode(self):
        return self._mode

    @property
    def temperature(self):
        return self._current_temperature
    
    @property
    def target_temperature(self):
        return self._current_temperature

    @property
    def device_identifier(self):
        return f"{self._device_address}"


class FloorHeating(Device):
    def __init__(self, buspro, device_address, channel, name=""):
        super().__init__(buspro, device_address, name)
        self._buspro = buspro
        self._device_address = device_address
        self._channel = channel
        self._status = None
        self._mode = 1 # Normal
        self._target_temperature = None
        self._current_temperature = None
        self._valve_status = None
        
        self.register_telegram_received_cb(self._telegram_received_cb)
        self._call_read_current_status(run_from_init=True)

    def _telegram_received_cb(self, telegram):
        if telegram.operate_code in [OperateCode.ReadFloorHeatingStatusNewResponse, OperateCode.ControlFloorHeatingStatusNewResponse]:
            channel = telegram.payload[0]
            if channel == self._channel:
                work = telegram.payload[1]
                self._status = (work & 0x0F)
                self._mode = telegram.payload[3]
                self._target_temperature = telegram.payload[4]
                if len(telegram.payload) > 9:
                    self._valve_status = bool(telegram.payload[9])
                self._call_device_updated()

        elif telegram.operate_code == OperateCode.ReadFloorHeatingTemperatureNewResponse:
            channel = telegram.payload[0]
            if channel == self._channel:
                try:
                    self._current_temperature = struct.unpack('<f', bytes(telegram.payload[1:5]))[0]
                    self._call_device_updated()
                except Exception:
                    pass

        elif telegram.operate_code == OperateCode.ReadFloorHeatingTemperatureLegacyResponse:
            channel = telegram.payload[0]
            if channel == self._channel:
                raw_temp = telegram.payload[1]
                sign = -1 if (raw_temp >> 7) else 1
                self._current_temperature = sign * (raw_temp & 0x7F)
                self._call_device_updated()

    async def read_status(self):
        # Read floor heating channel status
        rfhs = _ReadFloorHeatingStatusNew(self._buspro)
        rfhs.subnet_id, rfhs.device_id = self._device_address
        rfhs.channel = self._channel
        await rfhs.send()

        # Read temperature (try new first)
        rfht = _ReadFloorHeatingTemperatureNew(self._buspro)
        rfht.subnet_id, rfht.device_id = self._device_address
        rfht.channel = self._channel
        await rfht.send()

        # Also send legacy read as fallback
        rfhl = _ReadFloorHeatingTemperatureLegacy(self._buspro)
        rfhl.subnet_id, rfhl.device_id = self._device_address
        rfhl.channel = self._channel
        await rfhl.send()

    async def control_status(self, status=None, mode=None, target_temperature=None):
        cfhs = _ControlFloorHeatingStatusNew(self._buspro)
        cfhs.subnet_id, cfhs.device_id = self._device_address
        cfhs.channel = self._channel
        
        # Use current values if not specified
        cfhs.work_status = status if status is not None else (self._status == 1)
        cfhs.mode = mode if mode is not None else self._mode
        
        target = target_temperature if target_temperature is not None else self._target_temperature
        if target is None:
            target = 25
        cfhs.temp_normal = int(target)
        cfhs.temp_day = int(target)
        cfhs.temp_night = int(target)
        cfhs.temp_away = int(target)
        
        await cfhs.send()

    def _call_read_current_status(self, run_from_init=False):
        async def read_current_status():
            if run_from_init:
                await asyncio.sleep(5)
            await self.read_status()

        asyncio.ensure_future(read_current_status(), loop=self._buspro.loop)

    @property
    def is_on(self):
        return self._status == 1

    @property
    def mode(self):
        return self._mode

    @property
    def temperature(self):
        return self._current_temperature
    
    @property
    def target_temperature(self):
        return self._target_temperature

    @property
    def valve_status(self):
        return self._valve_status

    @property
    def device_identifier(self):
        return f"{self._device_address}-{self._channel}"

