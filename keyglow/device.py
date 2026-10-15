"""Keyboard protocol for the HyperX "Mars" keyboard (USB 0951:16C6).

The keyboard uses a Sonix controller. Commands are 64-byte HID feature
reports on the keyboard interface; see docs/PROTOCOL.md. The raw report
I/O comes from a per-platform transport.
"""

import sys
import threading
import time

from .protocol import PACKET, DeviceError

if sys.platform == "win32":
    from .transport_windows import Transport
else:
    from .transport_linux import Transport

__all__ = ["DeviceError", "Keyboard"]


class Keyboard:
    """One open connection to the keyboard's control interface."""

    def __init__(self, transport):
        self._t = transport
        self.path = transport.path
        self.lock = threading.Lock()
        self.version = self._read_version()

    @classmethod
    def find(cls):
        transport = Transport.find()
        return cls(transport) if transport else None

    def close(self):
        self._t.close()

    # -- raw packets -------------------------------------------------------
    def send(self, data):
        self._t.send(bytes(data)[:PACKET])

    def recv(self):
        return self._t.recv()

    def command(self, cmd, extra=b"", wait=0.03):
        """Send a 04 <cmd> command and return the reply. Reply byte 3 == 1 means OK."""
        self.send(bytes([0x04, cmd, 0, 0]) + bytes(extra))
        time.sleep(wait)
        return self.recv()

    # -- protocol ----------------------------------------------------------
    def _read_version(self):
        """Firmware version from the 2-chunk info block (04 05), e.g. 0x0100."""
        try:
            with self.lock:
                self.command(0x05, bytes(4) + b"\x02")
                info = self.recv()
            return int.from_bytes(info[8:10], "little")
        except DeviceError:
            return 0

    def is_ready(self):
        with self.lock:
            return self.command(0xE0)[3] == 1

    def write_block(self, cmd, payload, chunk_delay=0.004):
        """Bulk write as done by the vendor software: header, 64-byte chunks, checksum check."""
        n = (len(payload) + PACKET - 1) // PACKET
        payload = bytes(payload) + bytes(n * PACKET - len(payload))
        with self.lock:
            for _ in range(10):
                reply = self.command(cmd, bytes(4) + bytes([n & 0xFF, n >> 8]))
                if reply[3] == 1:
                    break
                time.sleep(0.1)
            else:
                raise DeviceError("The keyboard did not accept the command. Try reconnecting it.")
            for i in range(n):
                self.send(payload[i * PACKET:(i + 1) * PACKET])
                time.sleep(chunk_delay)
            reply = self.command(0x02)
            device_sum = int.from_bytes(reply[4:8], "little")
            if reply[3] != 1 or device_sum != sum(payload):
                raise DeviceError("The keyboard rejected the data (checksum mismatch).")
