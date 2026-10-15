"""Constants shared by the platform transports."""

VID = 0x0951
PID = 0x16C6
FEATURE_LEN = 65           # report ID + 64 data bytes
PACKET = 64


class DeviceError(Exception):
    pass
