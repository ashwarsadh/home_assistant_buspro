import asyncio
import socket
import time


class UDPClient:
    """UDP transport for the HDL gateway, with automatic recovery.

    Without recovery a dead socket made the integration silently deaf: no
    telegrams ever arrived again and every entity kept its last state until
    Home Assistant was restarted, while optimistic state writes made the UI
    look healthy.

    Liveness is judged by received traffic. The bus is continuously chatty
    independently of Home Assistant (logic modules poll dry contacts, panels
    broadcast): measured on the real bus during the quietest hour at ~5
    telegrams/sec with a worst-case gap of 4.5s, so silence far beyond that
    means our socket died rather than the bus going idle.
    """

    RX_SILENCE_TIMEOUT = 180      # ~40x the worst observed inter-telegram gap
    WATCHDOG_INTERVAL = 30
    RECONNECT_BACKOFF = (0, 1, 2, 5, 10, 30, 60)   # 0 => first attempt is immediate

    class UDPClientFactory(asyncio.DatagramProtocol):

        def __init__(self, buspro, generation, data_received_callback=None, connection_lost_callback=None):
            self.buspro = buspro
            self.generation = generation
            self.transport = None
            self.data_received_callback = data_received_callback
            self.connection_lost_callback = connection_lost_callback

        def connection_made(self, transport):
            self.transport = transport

        def datagram_received(self, data, address):
            if self.data_received_callback is not None:
                self.data_received_callback(data, address)

        def error_received(self, exc):
            # Routine for UDP (e.g. ICMP port-unreachable while the gateway
            # reboots) and NOT a reason to recycle: a socket that is genuinely
            # dead stops delivering telegrams and the watchdog picks that up.
            self.buspro.logger.warning('Error received: %s', exc)

        def connection_lost(self, exc):
            self.buspro.logger.warning('Buspro UDP transport closed: %s', exc)
            if self.connection_lost_callback is not None:
                self.connection_lost_callback(self.generation, exc)

    def __init__(self, buspro, gateway_address_send_receive, callback):
        self.buspro = buspro
        self._gateway_address_send, self._gateway_address_receive = gateway_address_send_receive
        self.callback = callback
        self.transport = None
        self._generation = 0
        self._last_rx = None
        self._stopping = False
        self._reconnecting = False
        self._watchdog_task = None
        self._reconnect_task = None

    def _data_received_callback(self, data, address):
        self._last_rx = time.monotonic()
        self.callback(data, address)

    def _close_transport(self):
        old, self.transport = self.transport, None
        if old is not None:
            try:
                old.close()
            except Exception:
                pass

    def _create_multicast_sock(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setblocking(False)
            sock.bind(self._gateway_address_receive)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 0)
            return sock
        except Exception as ex:
            self.buspro.logger.warning("Could not connect to {}: {}".format(self._gateway_address_receive, ex))

    async def _connect(self):
        try:
            self._generation += 1
            factory = UDPClient.UDPClientFactory(
                self.buspro, self._generation,
                data_received_callback=self._data_received_callback,
                connection_lost_callback=self._on_connection_lost)

            sock = self._create_multicast_sock()
            if sock is None:
                self.buspro.logger.warning("Socket is None")
                return

            (transport, _) = await self.buspro.loop.create_datagram_endpoint(lambda: factory, sock=sock)

            if self._stopping:            # stopped while we were connecting
                transport.close()
                return

            self.transport = transport
            self._last_rx = time.monotonic()
        except Exception as ex:
            self.buspro.logger.warning("Could not create endpoint to {}: {}".format(self._gateway_address_receive, ex))

    def _on_connection_lost(self, generation, exc):
        if self._stopping:
            return
        # Ignore the dying breath of a socket we already replaced, otherwise it
        # would null out the healthy transport that succeeded it.
        if generation != self._generation:
            return
        self._close_transport()
        self._schedule_reconnect()

    def _schedule_reconnect(self):
        if self._stopping or self._reconnecting:
            return
        if self._reconnect_task is not None and not self._reconnect_task.done():
            return
        self._reconnect_task = asyncio.ensure_future(self._reconnect(), loop=self.buspro.loop)

    async def _reconnect(self):
        if self._reconnecting or self._stopping:
            return
        self._reconnecting = True
        try:
            for delay in self.RECONNECT_BACKOFF:
                if self._stopping:
                    return
                if delay:
                    await asyncio.sleep(delay)
                if self._stopping:        # stop() landed during the backoff sleep
                    return
                self._close_transport()
                await self._connect()
                if self._stopping:
                    self._close_transport()
                    return
                if self.transport is not None:
                    self.buspro.logger.warning("Buspro UDP socket reconnected")
                    return
                self.buspro.logger.warning("Buspro UDP reconnect failed, retrying")
        finally:
            self._reconnecting = False

    async def _watchdog(self):
        # connection_lost is not raised for every way a socket can go bad, so
        # also recover from "no traffic" and "never connected".
        while not self._stopping:
            await asyncio.sleep(self.WATCHDOG_INTERVAL)
            if self._stopping or self._reconnecting:
                continue
            if self.transport is None:
                self.buspro.logger.warning("Buspro UDP transport is down - reconnecting")
                await self._reconnect()
                continue
            if self._last_rx is None:
                continue
            silence = time.monotonic() - self._last_rx
            if silence > self.RX_SILENCE_TIMEOUT:
                self.buspro.logger.warning(
                    "No telegrams for %.0fs - recycling Buspro UDP socket", silence)
                self._last_rx = time.monotonic()   # don't retrigger while reconnecting
                await self._reconnect()

    async def start(self):
        self._stopping = False
        self._last_rx = time.monotonic()   # arm the watchdog even if this connect fails
        await self._connect()
        if self._watchdog_task is None or self._watchdog_task.done():
            self._watchdog_task = asyncio.ensure_future(self._watchdog(), loop=self.buspro.loop)
        if self.transport is None:
            self._schedule_reconnect()

    async def stop(self):
        self._stopping = True
        for attr in ("_watchdog_task", "_reconnect_task"):
            task = getattr(self, attr)
            if task is not None:
                task.cancel()
                setattr(self, attr, None)
        self._close_transport()

    async def send_message(self, message):
        if self.transport is None:
            self.buspro.logger.info("Could not send message. Transport is None.")
            self._schedule_reconnect()
            return
        try:
            self.transport.sendto(message, self._gateway_address_send)
        except OSError as ex:
            # asyncio funnels ordinary socket errors to error_received, so
            # reaching here means the transport object itself is unusable.
            self.buspro.logger.warning("Send failed (%s) - recycling socket", ex)
            self._close_transport()
            self._schedule_reconnect()
