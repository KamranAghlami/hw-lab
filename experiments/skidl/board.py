#!/usr/bin/env python3
"""Approach C (code-first): the same board in SKiDL 3.0.

SKiDL describes connectivity in Python; netlist generation is native, schematic
drawing is delegated to the `schematizer` package (auto placement + routing).
Outputs into experiments/skidl/out/.
"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
os.environ.setdefault("KICAD10_SYMBOL_DIR", str(ROOT / "hardware/lib"))
from skidl import Net, Part, generate_netlist, generate_schematic, lib_search_paths, set_default_tool, KICAD10  # noqa: E402

set_default_tool(KICAD10)
lib_search_paths[KICAD10] = [str(ROOT / "hardware/lib")]
L = "hwlab.kicad_sym"


def P(name, ref):
    return Part(L, name, ref=ref)


gnd, v3, vbus = Net("GND"), Net("+3V3"), Net("VBUS")
for n in (gnd, v3, vbus):
    n.drive = 3  # POWER: stands in for PWR_FLAG
dp, dn, cc1, cc2 = Net("USB_DP"), Net("USB_DN"), Net("CC1"), Net("CC2")
en, boot, tx, rx = Net("EN"), Net("BOOT"), Net("UART_TX"), Net("UART_RX")
sda, scl, int1, int2, led, led_a = (Net(n) for n in ("I2C_SDA", "I2C_SCL", "IMU_INT1", "IMU_INT2", "LED", "LED_A"))

j1 = P("USB_C_HRO_TYPE-C-31-M-12", "J1")
vbus += j1["VBUS"]; gnd += j1["GND"], j1["SHIELD"]; cc1 += j1["CC1"]; cc2 += j1["CC2"]
dp += j1["A6"], j1["B6"]; dn += j1["A7"], j1["B7"]
for ref, net in (("R1", cc1), ("R2", cc2)):
    r = P("R_5k1_0402", ref); net & r & gnd

u2 = P("AMS1117-3.3", "U2"); vbus += u2["VI"]; v3 += u2["VO"]; gnd += u2["GND"]
c = P("C_10u_0603", "C1"); vbus & c & gnd
c = P("C_22u_0805", "C2"); v3 & c & gnd

u1 = P("ESP32-S3-WROOM-1-N8", "U1")
v3 += u1["3V3"]; gnd += u1["GND"]; en += u1["EN"]; boot += u1["IO0"]
dn += u1["USB_D-"]; dp += u1["USB_D+"]; tx += u1["TXD0"]; rx += u1["RXD0"]
sda += u1["IO8"]; scl += u1["IO9"]; int1 += u1["IO10"]; int2 += u1["IO11"]; led += u1["IO38"]
c = P("C_100n_0402", "C3"); v3 & c & gnd
c = P("C_10u_0603", "C7"); v3 & c & gnd
r = P("R_10k_0402", "R3"); v3 & r & en
c = P("C_1u_0402", "C4"); en & c & gnd
s = P("SW_TS-1187A-B-A-B", "SW2"); en & s & gnd
s = P("SW_TS-1187A-B-A-B", "SW1"); boot & s & gnd
r = P("R_1k_0402", "R6"); led & r & led_a
d = P("LED_Green_0805", "D1"); led_a += d["A"]; gnd += d["K"]

u3 = P("LSM6DSOTR", "U3")
v3 += u3["VDD"], u3["VDDIO"], u3["CS"]; gnd += u3["GND"], u3["SDO/SA0"], u3["SDX"], u3["SCX"]
sda += u3["SDA"]; scl += u3["SCL"]; int1 += u3["INT1"]; int2 += u3["INT2"]
for ref in ("C5", "C6"):
    c = P("C_100n_0402", ref); v3 & c & gnd
r = P("R_4k7_0402", "R4"); v3 & r & sda
r = P("R_4k7_0402", "R5"); v3 & r & scl

j2 = P("JST_SH_SM04B-SRSS-TB", "J2")
gnd += j2[1]; v3 += j2[2]; tx += j2[3]; rx += j2[4]

if __name__ == "__main__":
    out = HERE / "out"
    out.mkdir(exist_ok=True)
    generate_netlist(file_=str(out / "hwlab.net"))
    try:
        generate_schematic(filepath=str(out), top_name="hwlab", title="hw-lab (SKiDL)")
    except Exception as e:  # record, don't hide
        print("generate_schematic FAILED:", type(e).__name__, e)
        raise
