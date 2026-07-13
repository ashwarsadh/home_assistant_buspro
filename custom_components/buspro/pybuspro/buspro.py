''' pybuspro version 1.0.0  '''

import asyncio
import logging

from .helpers.enums import *
from .transport.network_interface import NetworkInterface


# ip, port = gateway_address
# subnet_id, device_id, channel = device_address


class StateUpdater:
    def __init__(self, buspro, sleep=10):
        self.buspro = buspro
        self.run_forever = True
        self.run_task = None
        self.sleep = sleep

    async def start(self):
        self.run_task = self.buspro.loop.create_task(self.run())

    async def run(self):
        await asyncio.sleep(0)
        self.buspro.logger.info("Starting StateUpdater with {} seconds interval".format(self.sleep))

        while True:
            await asyncio.sleep(self.sleep)
            await self.buspro.sync()


class Buspro:

    def __init__(self, gateway_address_send_receive, loop_=None):
        self.loop = loop_ or asyncio.get_event_loop()
        self.state_updater = None
        self.started = False
        self.network_interface = None
        self.logger = logging.getLogger("buspro.log")
        self.telegram_logger = logging.getLogger("buspro.telegram")

        self.callback_all_messages = None
        self._telegram_received_cbs = []
        # device_address (tuple) -> list of cb entries, so each incoming
        # telegram dispatches in O(matching) instead of scanning every
        # registered entity callback (~300 on this installation).
        self._telegram_received_cbs_by_addr = {}

        self.gateway_address_send_receive = gateway_address_send_receive

    def __del__(self):
        if self.started:
            try:
                task = self.loop.create_task(self.stop())
                self.loop.run_until_complete(task)
            except RuntimeError as exp:
                self.logger.warning("Could not close loop, reason: {}".format(exp))

    # noinspection PyUnusedLocal
    async def start(self, state_updater=False):  # , daemon_mode=False):
        self.network_interface = NetworkInterface(self, self.gateway_address_send_receive)
        self.network_interface.register_callback(self._callback_all_messages)
        await self.network_interface.start()

        if state_updater:
            self.state_updater = StateUpdater(self)
            await self.state_updater.start()

        '''
        if daemon_mode:
            await self._loop_until_sigint()
        '''

        self.started = True

        # await asyncio.sleep(5)
        # await self.network_interface.send_message(b'\0x01')

    async def stop(self):
        await self._stop_network_interface()
        self.started = False

    def _callback_all_messages(self, telegram):
        # Telegram.__str__ JSON-encodes the whole packet; only pay that cost
        # when the buspro.telegram logger is actually at debug level.
        if self.telegram_logger.isEnabledFor(logging.DEBUG):
            self.telegram_logger.debug(telegram)

        if self.callback_all_messages is not None:
            self.callback_all_messages(telegram)

        if telegram.operate_code is OperateCode.TIME_IF_FROM_LOGIC_OR_SECURITY:
            return

        # Sender callback kun for oppgitt kanal
        addresses = {self._addr_key(telegram.target_address), self._addr_key(telegram.source_address)}
        for address in addresses:
            for telegram_received_cb in self._telegram_received_cbs_by_addr.get(address, ()):
                postfix = telegram_received_cb['postfix']
                if postfix is not None:
                    telegram_received_cb['callback'](telegram, postfix)
                else:
                    telegram_received_cb['callback'](telegram)

    @staticmethod
    def _addr_key(device_address):
        return tuple(device_address) if device_address is not None else None

    async def _stop_network_interface(self):
        if self.network_interface is not None:
            await self.network_interface.stop()
            self.network_interface = None

    def register_telegram_received_all_messages_cb(self, telegram_received_cb):
        self.callback_all_messages = telegram_received_cb

    def register_telegram_received_device_cb(self, telegram_received_cb, device_address, postfix=None):
        entry = {
            'callback': telegram_received_cb,
            'device_address': device_address,
            'postfix': postfix}
        self._telegram_received_cbs.append(entry)
        self._telegram_received_cbs_by_addr.setdefault(self._addr_key(device_address), []).append(entry)

    def unregister_telegram_received_device_cb(self, telegram_received_cb, device_address, postfix=None):
        entry = {
            'callback': telegram_received_cb,
            'device_address': device_address,
            'postfix': postfix}
        self._telegram_received_cbs.remove(entry)
        key = self._addr_key(device_address)
        bucket = self._telegram_received_cbs_by_addr.get(key)
        if bucket is not None:
            bucket.remove(entry)
            if not bucket:
                del self._telegram_received_cbs_by_addr[key]

    @staticmethod
    async def sync():
        # await self.callback("LOG: Sync() triggered from StateUpdater")
        # print("LOG: Sync() triggered from StateUpdater")
        raise NotImplementedError
