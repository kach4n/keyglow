"""Gaming mode: blocks the Windows key, Alt+Tab and/or Alt+F4 while KeyGlow runs.

Uses a low-level keyboard hook (WH_KEYBOARD_LL) on its own thread, the same
way the vendor software implements this feature.
"""

import ctypes
import ctypes.wintypes as wt
import threading

WH_KEYBOARD_LL = 13
WM_QUIT = 0x0012
LLKHF_ALTDOWN = 0x20
VK_TAB, VK_F4, VK_LWIN, VK_RWIN = 0x09, 0x73, 0x5B, 0x5C

_user32 = ctypes.WinDLL("user32", use_last_error=True)
_k32 = ctypes.WinDLL("kernel32", use_last_error=True)

LRESULT = ctypes.c_ssize_t
HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wt.WPARAM, wt.LPARAM)


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [("vkCode", wt.DWORD), ("scanCode", wt.DWORD), ("flags", wt.DWORD),
                ("time", wt.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


_user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, wt.HINSTANCE, wt.DWORD]
_user32.SetWindowsHookExW.restype = wt.HHOOK
_user32.CallNextHookEx.argtypes = [wt.HHOOK, ctypes.c_int, wt.WPARAM, wt.LPARAM]
_user32.CallNextHookEx.restype = LRESULT
_user32.UnhookWindowsHookEx.argtypes = [wt.HHOOK]
_user32.PostThreadMessageW.argtypes = [wt.DWORD, wt.UINT, wt.WPARAM, wt.LPARAM]
_k32.GetModuleHandleW.restype = wt.HMODULE


class GamingMode:
    def __init__(self):
        self.block_win = self.block_alt_tab = self.block_alt_f4 = False
        self._thread = None
        self._thread_id = None
        self._proc = HOOKPROC(self._hook)

    @property
    def active(self):
        return self.block_win or self.block_alt_tab or self.block_alt_f4

    def configure(self, win=False, alt_tab=False, alt_f4=False):
        self.block_win, self.block_alt_tab, self.block_alt_f4 = bool(win), bool(alt_tab), bool(alt_f4)
        if self.active and not self._thread:
            started = threading.Event()
            self._thread = threading.Thread(target=self._run, args=(started,), daemon=True)
            self._thread.start()
            started.wait(2)
        elif not self.active:
            self.stop()

    def stop(self):
        if self._thread_id:
            _user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
        if self._thread:
            self._thread.join(2)
        self._thread = self._thread_id = None

    def _hook(self, code, wparam, lparam):
        if code == 0:
            k = ctypes.cast(lparam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
            alt = bool(k.flags & LLKHF_ALTDOWN)
            if (self.block_win and k.vkCode in (VK_LWIN, VK_RWIN)) \
                    or (self.block_alt_tab and alt and k.vkCode == VK_TAB) \
                    or (self.block_alt_f4 and alt and k.vkCode == VK_F4):
                return 1
        return _user32.CallNextHookEx(None, code, wparam, lparam)

    def _run(self, started):
        self._thread_id = _k32.GetCurrentThreadId()
        hook = _user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._proc, _k32.GetModuleHandleW(None), 0)
        started.set()
        msg = wt.MSG()
        while _user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            _user32.TranslateMessage(ctypes.byref(msg))
            _user32.DispatchMessageW(ctypes.byref(msg))
        if hook:
            _user32.UnhookWindowsHookEx(hook)
