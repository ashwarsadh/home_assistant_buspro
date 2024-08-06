import asyncio
import datetime
from .control import _CoverControl, _ReadCoverStatus
from .device import Device
from ..helpers.enums import *
from ..helpers.generics import Generics
from homeassistant.const import (
    STATE_CLOSING,
    STATE_OPENING,
)
import logging
_LOGGER = logging.getLogger(__name__)

class Cover(Device):
    def __init__(self, buspro, device_address, channel_number, name="", opening_time=20, delay_read_current_state_seconds=0):
        super().__init__(buspro, device_address, name)
        # device_address = (subnet_id, device_id, channel_number)

        self._buspro = buspro
        self._device_address = device_address
        self._channel = channel_number
        #self._status = CoverStatus.CLOSE
        self._status = CoverStatus.OPEN
        self._command=None
        self._requested_position=None
        self._position=1
        self._opening_time=opening_time #time it takes to open curtain, set to 20 sec by default
        self._state_changetime=opening_time
        self._start_time = None #time at which curtain started to open or close to calculate start_time
        self.register_telegram_received_cb(self._telegram_received_cb)
        self._call_read_current_status_of_channels(run_from_init=True)

    def _telegram_received_cb(self, telegram):
        if telegram.operate_code == OperateCode.CurtainSwitchControlResponse:
            channel = telegram.payload[0]
            #status = telegram.payload[1]
            if channel == self._channel:
             #   self._status = status
                self._call_device_updated()
        elif telegram.operate_code == OperateCode.CurtainSwitchStatusResponse:
           # if self._channel <= telegram.payload[0]:
            #    if len(telegram.payload) > 1:
             #       self._status = telegram.payload[1]
                self._call_device_updated()

    async def set_stop(self):
        await self._set(CoverStatus.STOP)

    async def set_open(self):
        await self._set(CoverStatus.OPEN)

    async def set_close(self):
        await self._set(CoverStatus.CLOSE)

    async def set_position(self,position):
        self._requested_position=position
        if self._status == CoverStatus.OPEN:
            self._status = STATE_CLOSING
        else:
            self._status = STATE_OPENING
        self._command = CoverStatus.CLOSE
        self._start_time = datetime.datetime.now()
        self._state_changetime = self._opening_time+((position/100)*self._opening_time) # will take 30 seconds to do 50% for 20s assumed time
        await self._send_command()#first close the curtain completely to set current state
        self._call_device_updated()
        await asyncio.sleep(self._opening_time)# wait till its closed
        self._command = CoverStatus.OPEN
        await self._send_command()#then open it
        await asyncio.sleep((position/100)*self._opening_time)# if 50% position then wait for 15 seconds if opening time is 30
        self._command = CoverStatus.STOP
        await self._send_command()#then Stop it
        if self._status == STATE_OPENING:
            self._status = CoverStatus.CLOSE
        else:
            self._status = CoverStatus.OPEN
        self._state_changetime=self._opening_time#reset for further use
        self._position=position#saves current position
        self._call_device_updated()



    async def read_status(self):
        rfhs = _ReadCoverStatus(self._buspro)
        rfhs.subnet_id, rfhs.device_id = self._device_address
        rfhs.channel_number=self._channel
        await rfhs.send()
    
    def _call_read_current_status_of_channels(self, run_from_init=False):

        async def read_current_status_of_channels():
            if run_from_init:
                await asyncio.sleep(5)

            rfhs = _ReadCoverStatus(self._buspro)
            rfhs.subnet_id, rfhs.device_id = self._device_address
            rfhs.channel_number=self._channel
            await rfhs.send()

        asyncio.ensure_future(read_current_status_of_channels(), loop=self._buspro.loop)

    @property
    def is_closed(self):
        #return None
        #return True
        if self._status == CoverStatus.CLOSE and self._command == CoverStatus.CLOSE:
            return True
        else:
           return False

    @property
    def is_closing(self):
        if self._status == STATE_CLOSING:
            return True
        else:
           return False

    @property
    def is_opening(self):
        if self._status == STATE_OPENING:
            return True
        else:
           return False

    @property
    def current_cover_position(self):
        currentposition=None
        if self._status == STATE_OPENING:
            if self._position:
                currentposition=self._position
            else:
                currentposition=1
            elapsed_time = (datetime.datetime.now() - self._start_time).total_seconds()
            _LOGGER.debug("Curtain Opening '{}' elapsed time is {} current position is {} time to change position i {}".format(self._device_address, elapsed_time,
                                                                                        currentposition, self._state_changetime))
            if elapsed_time < self._state_changetime:
                difference=self._requested_position-currentposition
                difference_completed=elapsed_time / self._state_changetime
                self._position=int(currentposition+(difference*difference_completed))
                _LOGGER.debug("Curtain Opening '{}' difference of change is {} completed diff % is {} and current position is {}".format(self._device_address, difference,
                                                                                        difference_completed, self._position))
                return self._position
            self._position=99 #to keep it openable if position was out of sync
            return self._position
        elif self._status == STATE_CLOSING:
            if self._position:
                currentposition=self._position
            else:
                currentposition=99
            elapsed_time = (datetime.datetime.now() - self._start_time).total_seconds()
            if elapsed_time < self._state_changetime:
                difference=currentposition-self._requested_position
                difference_completed=elapsed_time / self._state_changetime
                self._position=int(currentposition-(difference*difference_completed))
                #self._position=int(100 - (elapsed_time / self._state_changetime) * 100)
                return self._position
            self._position =1
            return 1
        elif self._status == CoverStatus.OPEN:
            if self._position:
                return self._position
            return 99
        elif self._status == CoverStatus.CLOSE:
            if self._position:
                return self._position
            return 1
        else:
            return None
    @property
    def device_identifier(self):
        return f"{self._device_address}-{self._channel}"

    async def _set(self, status):
        if status in [CoverStatus.OPEN, CoverStatus.CLOSE]:
            self._start_time = datetime.datetime.now()
            if status == CoverStatus.CLOSE:
                self._requested_position=1
            else:
                self._requested_position=99
            # Determine intermediate status
            intermediate_status = STATE_OPENING if status == CoverStatus.OPEN else STATE_CLOSING
            if self._position: #if current position is known
                if status == CoverStatus.CLOSE:
                    self._state_changetime = (self._position/100)*self._opening_time # will take 18 seconds to close from 90% if opening time is 20
                else:
                    self._state_changetime = ((100-self._position)/100)*self._opening_time # will take 2 seconds to open from 90% to 100%
            # Set intermediate status and send command immediately
            self._command=status #tells buspro to close or open
            self._status = intermediate_status
            self._call_device_updated()
            await self._send_command()

            # Schedule task to update to final status after 30 seconds
            asyncio.create_task(self._update_status_after_delay(self._requested_position))
        else: # incase of stop
            # For other statuses, set directly and send command
            self._status = status
            self._command = status
            await self._send_command()

    async def _update_status_after_delay(self, request_position ):
        await asyncio.sleep(self._state_changetime)  # Wait for 20 seconds
        if self._command in [CoverStatus.OPEN, CoverStatus.CLOSE]:#STOP has not been pressed meanwhile in 30 sec
            self._position=request_position
            self._status = self._command
            self._call_device_updated()
        #await self._send_command()

    async def _send_command(self):
        scc = _CoverControl(self._buspro)
        scc.subnet_id, scc.device_id = self._device_address
        scc.channel_number = self._channel
        scc.channel_status = self._command
        await scc.send()

    
    #async def _set(self, status):
    #    self._status = status

    #    scc = _CoverControl(self._buspro)
    #    scc.subnet_id, scc.device_id = self._device_address
    #    scc.channel_number = self._channel
    #    scc.channel_status = self._status
    #    await scc.send()
