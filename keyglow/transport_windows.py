"""Windows transport: HID feature reports through hid.dll (pure ctypes).

Windows does not let applications read or write a keyboard collection, but
it does allow feature reports on a handle opened with zero access rights,
which is what the vendor software does too.
"""

import ctypes
import ctypes.wintypes as wt

from .protocol import FEATURE_LEN, PID, VID, DeviceError

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
_hid.HidD_GetPreparsedData.argtypes = [wt.HANDLE, ctypes.POINTER(ctypes.c_void_p)]
_hid.HidD_FreePreparsedData.argtypes = [ctypes.c_void_p]
_hid.HidP_GetCaps.argtypes = [ctypes.c_void_p, ctypes.POINTER(HIDP_CAPS)]


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


class Transport:
    def __init__(self, handle, path):
        self._h = handle
        self.path = path

    @classmethod
    def find(cls):
        for path in _hid_paths():
            if f"vid_{VID:04x}&pid_{PID:04x}" not in path.lower():
                continue
            h = _open(path)
            if not h:
                continue
            if _feature_len(h) == FEATURE_LEN:
                return cls(h, path)
            _k32.CloseHandle(h)
        return None

    def send(self, packet):
        buf = (ctypes.c_ubyte * FEATURE_LEN)(0, *packet)
        if not _hid.HidD_SetFeature(self._h, buf, FEATURE_LEN):
            raise DeviceError(f"Sending to the keyboard failed (error {ctypes.get_last_error()})")

    def recv(self):
        buf = (ctypes.c_ubyte * FEATURE_LEN)()
        if not _hid.HidD_GetFeature(self._h, buf, FEATURE_LEN):
            raise DeviceError(f"Reading from the keyboard failed (error {ctypes.get_last_error()})")
        return bytes(buf)[1:]

    def close(self):
        if self._h:
            _k32.CloseHandle(self._h)
            self._h = None
