"""
Async syslog receiver for UDP/TCP.
"""
from __future__ import annotations

import asyncio
import os
from typing import Callable, Iterable, List

from hcai_ops.data.ingest import parse_syslog_lines
from hcai_ops.data.schemas import HCaiEvent
from hcai_ops.analytics import event_store


class SyslogReceiver:
    def __init__(self, udp_port: int, tcp_port: int, event_handler: Callable[[HCaiEvent], None]):
        self.udp_port = udp_port
        self.tcp_port = tcp_port
        self.event_handler = event_handler
        self._udp_transport = None
        self._tcp_server = None

    def process_line(self, line: str) -> None:
        events = parse_syslog_lines([line])
        for evt in events:
            self.event_handler(evt)

    async def start_async(self) -> None:
        loop = asyncio.get_running_loop()

        class _UDP(asyncio.DatagramProtocol):
            def __init__(self, outer: "SyslogReceiver"):
                self.outer = outer

            def datagram_received(self, data, addr):  # type: ignore
                try:
                    line = data.decode(errors="ignore")
                    self.outer.process_line(line)
                except Exception:
                    pass

        self._udp_transport, _ = await loop.create_datagram_endpoint(
            lambda: _UDP(self), local_addr=("0.0.0.0", self.udp_port)
        )

        async def handle_tcp(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
            try:
                data = await reader.readline()
                line = data.decode(errors="ignore")
                self.process_line(line)
            except Exception:
                pass
            finally:
                writer.close()

        self._tcp_server = await asyncio.start_server(handle_tcp, "0.0.0.0", self.tcp_port)

    async def stop(self) -> None:
        if self._udp_transport:
            self._udp_transport.close()
        if self._tcp_server:
            self._tcp_server.close()
            await self._tcp_server.wait_closed()


def run_syslog_server_forever() -> None:
    enabled = os.getenv("HCAI_SYSLOG_ENABLED", "false").lower() == "true"
    udp_port = int(os.getenv("HCAI_SYSLOG_UDP_PORT", "5140"))
    tcp_port = int(os.getenv("HCAI_SYSLOG_TCP_PORT", "5141"))
    if not enabled:
        return

    receiver = SyslogReceiver(
        udp_port=udp_port,
        tcp_port=tcp_port,
        event_handler=lambda evt: event_store.add_events([evt]),
    )

    async def _main():
        await receiver.start_async()
        while True:
            await asyncio.sleep(3600)

    asyncio.run(_main())
