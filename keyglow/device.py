"""Low-level transport for the HyperX "Mars" keyboard (USB 0951:16C6).

The keyboard uses a Sonix controller. Commands are 64-byte HID feature
reports sent to the keyboard interface (feature report length 65 = report
ID 0 + 64 bytes). Windows does not let applications read or write a
keyboard collection, but it does allow feature reports on a handle opened
with zero access rights, which is what the vendor software does too.

Pure ctypes, no third-party dependencies.
"""

import ctypes
import ctypes.wintypes as wt
import threading
import time

VID = 0x0951
PID = 0x16C6
FEATURE_LEN = 65           # report ID + 64 data bytes
PACKET = 64

_hid = ctypes.WinDLL("hid")
_setupapi = ctypes.WinDLL("setupapi", use_last_error=True)
_k32 = ctypes.WinDLL("kernel32", use_last_error=True)

INVALID_HANDLE = wt.HANDLE(-1).value
DIGCF_PRESENT = 0x02
DIGCF_DEVICEINTERFACE = 0x10


class GUID(ctypes.Structure):
    _fields_ = [("Data1", wt.DWORD), ("Data2", wt.WORD), ("Data3", wt.WORD), ("Data4", ctypes.c_ubyte * 8)]


class SP_DEVICE_INTERFACE_DATA(ctypes.Structure):
    _fields_ = [("cbSize", wt.DWORD), ("InterfaceClassGuid", GUID), ("Flags", wt.DWORD), ("Reserved", ctypes.c_void_p)]


class HIDD_ATTRIBUTES(ctypes.Structure):
    _fields_ = [("Size", wt.ULONG), ("VendorID", wt.USHORT), ("ProductID", wt.USHORT), ("VersionNumber", wt.USHORT)]


class HIDP_CAPS(ctypes.Structure):
    _fields_ = [("Usage", wt.USHORT), ("UsagePage", wt.USHORT), ("InputReportByteLength", wt.USHORT),
                ("OutputReportByteLength", wt.USHORT), ("FeatureReportByteLength", wt.USHORT),
                ("Reserved", wt.USHORT * 17), ("Counts", wt.USHORT * 10)]


_k32.CreateFileW.restype = wt.HANDLE
_k32.CreateFileW.argtypes = [wt.LPCWSTR, wt.DWORD, wt.DWORD, ctypes.c_void_p, wt.DWORD, wt.DWORD, wt.HANDLE]
_k32.CloseHandle.argtypes = [wt.HANDLE]
_setupapi.SetupDiGetClassDevsW.restype = ctypes.c_void_p
_setupapi.SetupDiGetClassDevsW.argtypes = [ctypes.POINTER(GUID), wt.LPCWSTR, wt.HWND, wt.DWORD]
_setupapi.SetupDiEnumDeviceInterfaces.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(GUID), wt.DWORD,
                                                  ctypes.POINTER(SP_DEVICE_INTERFACE_DATA)]
_setupapi.SetupDiGetDeviceInterfaceDetailW.argtypes = [ctypes.c_void_p, ctypes.POINTER(SP_DEVICE_INTERFACE_DATA),
                                                       ctypes.c_void_p, wt.DWORD, ctypes.POINTER(wt.DWORD), ctypes.c_void_p]
_setupapi.SetupDiDestroyDeviceInfoList.argtypes = [ctypes.c_void_p]
_hid.HidD_SetFeature.argtypes = [wt.HANDLE, ctypes.c_void_p, wt.ULONG]
_hid.HidD_GetFeature.argtypes = [wt.HANDLE, ctypes.c_void_p, wt.ULONG]
_hid.HidD_GetAttributes.argtypes = [wt.HANDLE, ctypes.POINTER(HIDD_ATTRIBUTES)]
_hid.HidD_GetPreparsedData.argtypes = [wt.HANDLE, ctypes.POINTER(ctypes.c_void_p)]
_hid.HidD_FreePreparsedData.argtypes = [ctypes.c_void_p]
_hid.HidP_GetCaps.argtypes = [ctypes.c_void_p, ctypes.POINTER(HIDP_CAPS)]


class DeviceError(Exception):
    pass


def _hid_paths():
    guid = GUID()
    _hid.HidD_GetHidGuid(ctypes.byref(guid))
    info = _setupapi.SetupDiGetClassDevsW(ctypes.byref(guid), None, None, DIGCF_PRESENT | DIGCF_DEVICEINTERFACE)
    if not info or info == INVALID_HANDLE:
        return
    try:
        index = 0
        while True:
            data = SP_DEVICE_INTERFACE_DATA()
            data.cbSize = ctypes.sizeof(SP_DEVICE_INTERFACE_DATA)
            if not _setupapi.SetupDiEnumDeviceInterfaces(info, None, ctypes.byref(guid), index, ctypes.byref(data)):
                break
            index += 1
            needed = wt.DWORD()
            _setupapi.SetupDiGetDeviceInterfaceDetailW(info, ctypes.byref(data), None, 0, ctypes.byref(needed), None)
            buf = ctypes.create_string_buffer(needed.value)
            # cbSize of SP_DEVICE_INTERFACE_DETAIL_DATA_W: 8 on 64-bit, 6 on 32-bit
            ctypes.c_uint32.from_buffer(buf).value = 8 if ctypes.sizeof(ctypes.c_void_p) == 8 else 6
            if _setupapi.SetupDiGetDeviceInterfaceDetailW(info, ctypes.byref(data), buf, needed, None, None):
                yield ctypes.wstring_at(ctypes.addressof(buf) + 4)
    finally:
        _setupapi.SetupDiDestroyDeviceInfoList(info)


def _open(path):
    for access in (0xC0000000, 0):          # read/write first, then zero access like the vendor DLL
        h = _k32.CreateFileW(path, access, 3, None, 3, 0, None)
        if h and h != INVALID_HANDLE:
            return h
    return None


def _feature_len(handle):
    pp = ctypes.c_void_p()
    if not _hid.HidD_GetPreparsedData(handle, ctypes.byref(pp)):
        return 0
    caps = HIDP_CAPS()
    _hid.HidP_GetCaps(pp, ctypes.byref(caps))
    _hid.HidD_FreePreparsedData(pp)
    return caps.FeatureReportByteLength


class Keyboard:
    """One open connection to the keyboard's control interface."""

    def __init__(self, handle, path, version):
        self._h = handle
        self.path = path
        self.version = version
        self.lock = threading.Lock()

    @classmethod
    def find(cls):
        for path in _hid_paths():
            if f"vid_{VID:04x}&pid_{PID:04x}" not in path.lower():
                continue
            h = _open(path)
            if not h:
                continue
            attrs = HIDD_ATTRIBUTES()
            attrs.Size = ctypes.sizeof(HIDD_ATTRIBUTES)
            _hid.HidD_GetAttributes(h, ctypes.byref(attrs))
            if _feature_len(h) == FEATURE_LEN:
                return cls(h, path, attrs.VersionNumber)
            _k32.CloseHandle(h)
        return None

    def close(self):
        if self._h:
            _k32.CloseHandle(self._h)
            self._h = None

    # -- raw packets -------------------------------------------------------
    def send(self, data):
        data = bytes(data)[:PACKET]
        buf = (ctypes.c_ubyte * FEATURE_LEN)(0, *data)
        if not _hid.HidD_SetFeature(self._h, buf, FEATURE_LEN):
            raise DeviceError(f"Sending to the keyboard failed (error {ctypes.get_last_error()})")

    def recv(self):
        buf = (ctypes.c_ubyte * FEATURE_LEN)()
        if not _hid.HidD_GetFeature(self._h, buf, FEATURE_LEN):
            raise DeviceError(f"Reading from the keyboard failed (error {ctypes.get_last_error()})")
        return bytes(buf)[1:]

    def command(self, cmd, extra=b"", wait=0.03):
        """Send a 04 <cmd> command and return the reply. Reply byte 3 == 1 means OK."""
        self.send(bytes([0x04, cmd, 0, 0]) + bytes(extra))
        time.sleep(wait)
        return self.recv()

    # -- protocol ----------------------------------------------------------
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
