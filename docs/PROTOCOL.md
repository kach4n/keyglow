# Keyboard protocol notes

Notes on how the HyperX "Mars Gaming KeyBoard" (USB `0951:16C6`, Sonix controller,
firmware 1.00) is controlled. They come from static analysis of the vendor
software's installer (HyperX Genesis 2.2.1.4) and were checked on real hardware.
No vendor code or assets are included in this project.

## Transport

* HID interface 0 (the keyboard collection) has a 65-byte feature report:
  report ID `0` plus a 64-byte packet.
* Windows won't open keyboard collections for read/write, but feature reports
  work on a handle opened with **zero access rights**.
* Every command is `SetFeature(packet)` followed by `GetFeature()`. In the
  reply, byte 3 = `01` means accepted.

## Commands (first two bytes of the packet)

| Packet | Meaning |
|---|---|
| `04 E0` | Ready check |
| `04 05 … [8]=02` | Read 2 chunks of device info (VID/PID, firmware) |
| `04 08` + count | Write the key-assignment block (not used by KeyGlow) |
| `04 0A` + count | Write the **lighting block** |
| `04 0C` + count | Write the macro block (not used by KeyGlow) |
| `04 02` | Get the 32-bit sum of the bytes just written (bytes 4-7) |
| `04 AB`, `04 11`, `04 12`/`04 13` | Used by the firmware updater. **Do not send these.** |

A bulk write is: header `04 <cmd> 00 00 00 00 00 00 <chunks lo> <chunks hi>`
(retried until acknowledged), then the 64-byte chunks with a few ms between
them, then `04 02` to compare checksums.

**Every lighting write is stored in the keyboard's flash memory** and survives
unplugging. Don't stream animations through it.

## Lighting block (15 chunks, 960 bytes)

```
0x000  5 effect slots x 64 bytes (exactly five, or the keyboard rejects the block)
0x140  144 LEDs x 4 bytes: 80 RR GG BB
0x380  tail: [0]=active mode, [1]=custom brightness 0-5, [62..63]=AA 55
```

Mode bytes: `01` breathing, `03` spectrum cycling, `04` static, `05` wave,
`08` stack ("color loading"), `80` custom per-key. Modes `02`, `06` and `07`
are accepted but light nothing on this firmware (tested). This keyboard has
no reactive/ripple effects.

Effect slot fields (offset within the slot):

| Effect | Fields |
|---|---|
| Breathing | `[0]=01`, colors 1-5 as RGB at `1-15`, `[3C]` loop, `[3E]` brightness, `[3F]` speed |
| Spectrum | `[0]=03`, `[3E]` brightness, `[3F]` speed |
| Static | `[0]=04`, RGB at `1-3`, `[3E]` brightness |
| Wave | `[0]=05`, `[3D]` direction 0-3, `[3E]` brightness, `[3F]` speed |
| Stack | `[0]=08`, colors 1-5 at `1-15`, `[3C]` loop, `[3D]` direction, `[3E]` brightness, `[3F]` speed |

## LED index

A key's LED slot is `row * 18 + column` on the vendor's 8 x 18 key grid. The
exceptions are numpad 1/2/3, which sit at 140-142. The full map is in
`keyglow/layout.py`.
