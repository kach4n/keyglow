"""Linux transport: HID feature reports through /dev/hidraw* ioctls.

Needs read/write access to the keyboard's hidraw node; packaging/linux
ships a udev rule that grants it to the logged-in user.
"""

import fcntl
import os
from pathlib import Path

from .protocol import FEATURE_LEN, PID, VID, DeviceError

_HID_ID = f"0003:{VID:08X}:{PID:08X}"


def _ioc(direction, nr, size):
    # _IOC(dir, 'H', nr, size) from <asm-generic/ioctl.h>
    return (direction << 30) | (size << 16) | (ord("H") << 8) | nr


_IOC_RW = 3
HIDIOCSFEATURE = _ioc(_IOC_RW, 0x06, FEATURE_LEN)
HIDIOCGFEATURE = _ioc(_IOC_RW, 0x07, FEATURE_LEN)


def _keyboard_nodes():
    """hidraw nodes of the keyboard, the control interface (USB interface 0) first."""
    found = []
    for node in sorted(Path("/sys/class/hidraw").glob("hidraw*")):
        try:
            uevent = (node / "device" / "uevent").read_text()
        except OSError:
            continue
        if _HID_ID not in uevent.upper():
            continue
        phys = next((line for line in uevent.splitlines() if line.startswith("HID_PHYS=")), "")
        found.append((not phys.endswith("input0"), f"/dev/{node.name}"))
    return [path for _, path in sorted(found)]


class Transport:
    def __init__(self, fd, path):
        self._fd = fd
        self.path = path

    @classmethod
    def find(cls):
        denied = None
        for path in _keyboard_nodes():
            try:
                fd = os.open(path, os.O_RDWR)
            except PermissionError:
                denied = path
                continue
            transport = cls(fd, path)
            try:
                transport.recv()            # only the control interface answers feature reads
                return transport
            except DeviceError:
                transport.close()
        if denied:
            raise DeviceError(f"No permission to open {denied}. Install the udev rule (see README) and replug the keyboard.")
        return None

    def send(self, packet):
        buf = bytearray(FEATURE_LEN)
        buf[1:1 + len(packet)] = packet
        try:
            fcntl.ioctl(self._fd, HIDIOCSFEATURE, buf)
        except OSError as e:
            raise DeviceError(f"Sending to the keyboard failed ({e})") from e

    def recv(self):
        buf = bytearray(FEATURE_LEN)
        try:
            fcntl.ioctl(self._fd, HIDIOCGFEATURE, buf)
        except OSError as e:
            raise DeviceError(f"Reading from the keyboard failed ({e})") from e
        return bytes(buf[1:])

    def close(self):
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None
