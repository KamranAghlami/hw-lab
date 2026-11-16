#!/usr/bin/env python3
"""hw-lab test board — the design source (approach A: raw S-expression generator).

Edit this file, then run `python hardware/design.py` to regenerate
hardware/hwlab.kicad_sch. Parts come from hardware/lib/parts.toml (atomic parts:
footprint, MPN and LCSC are fixed per part). Power nets (GND, +3V3, VBUS) are
drawn with power symbols; every other net with labels.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tools"))
from schgen import Design, Library  # noqa: E402

lib = Library(HERE / "lib" / "hwlab.kicad_sym", "hwlab")
d = Design("hwlab", lib, title="hw-lab ESP32-S3 test board", rev="0.1", company="hw-lab")

# --- USB-C: power + native USB --------------------------------------------------
d.part("J1", "USB_C_HRO_TYPE-C-31-M-12", (40.64, 66.04),
       VBUS="VBUS", GND="GND", SHIELD="GND", CC1="CC1", CC2="CC2",
       A6="USB_DP", B6="USB_DP", A7="USB_DN", B7="USB_DN")
d.no_connect("J1", "SBU1", "SBU2")
d.part("R1", "R_5k1_0402", (88.9, 60.96), **{"1": "CC1", "2": "GND"})
d.part("R2", "R_5k1_0402", (99.06, 60.96), **{"1": "CC2", "2": "GND"})
d.part("#FLG01", "PWR_FLAG", (111.76, 55.88), **{"1": "VBUS"})
d.part("#FLG02", "PWR_FLAG", (121.92, 55.88), **{"1": "GND"})

# --- 3.3 V LDO ----------------------------------------------------------------------
d.part("U2", "AMS1117-3.3", (50.8, 127.0), VI="VBUS", VO="+3V3", GND="GND")
d.part("C1", "C_10u_0603", (76.2, 127.0), **{"1": "VBUS", "2": "GND"})
d.part("C2", "C_22u_0805", (86.36, 127.0), **{"1": "+3V3", "2": "GND"})

# --- ESP32-S3 module ---------------------------------------------------------------
d.part("U1", "ESP32-S3-WROOM-1-N8", (185.42, 88.9), **{
    "3V3": "+3V3", "GND": "GND", "EN": "EN", "IO0": "BOOT",
    "USB_D-": "USB_DN", "USB_D+": "USB_DP",
    "TXD0": "UART_TX", "RXD0": "UART_RX",
    "IO8": "I2C_SDA", "IO9": "I2C_SCL", "IO10": "IMU_INT1", "IO11": "IMU_INT2",
    "IO38": "LED",
})
d.no_connect("U1", rest=True)  # unused GPIOs
d.part("C3", "C_100n_0402", (226.06, 50.8), **{"1": "+3V3", "2": "GND"})
d.part("C7", "C_10u_0603", (236.22, 50.8), **{"1": "+3V3", "2": "GND"})
# EN: RC reset + reset button; IO0: boot button (internal pull-up)
d.part("R3", "R_10k_0402", (124.46, 93.98), **{"1": "+3V3", "2": "EN"})
d.part("C4", "C_1u_0402", (134.62, 93.98), **{"1": "EN", "2": "GND"})
d.part("SW2", "SW_TS-1187A-B-A-B", (129.54, 116.84), **{"1": "EN", "2": "GND"})
d.part("SW1", "SW_TS-1187A-B-A-B", (129.54, 132.08), **{"1": "BOOT", "2": "GND"})

# --- status LED ---------------------------------------------------------------------
d.part("R6", "R_1k_0402", (241.3, 121.92), **{"1": "LED", "2": "LED_A"})
d.part("D1", "LED_Green_0805", (256.54, 121.92), A="LED_A", K="GND")

# --- IMU (I2C mode: CS high, SA0 low -> address 0x6A) -------------------------------
d.part("U3", "LSM6DSOTR", (185.42, 157.48), **{
    "VDD": "+3V3", "VDDIO": "+3V3", "GND": "GND", "CS": "+3V3", "SDO/SA0": "GND",
    "SDA": "I2C_SDA", "SCL": "I2C_SCL", "INT1": "IMU_INT1", "INT2": "IMU_INT2",
    "SDX": "GND", "SCX": "GND",
})
d.part("C5", "C_100n_0402", (231.14, 170.18), **{"1": "+3V3", "2": "GND"})
d.part("C6", "C_100n_0402", (241.3, 170.18), **{"1": "+3V3", "2": "GND"})
d.part("R4", "R_4k7_0402", (231.14, 147.32), **{"1": "+3V3", "2": "I2C_SDA"})
d.part("R5", "R_4k7_0402", (241.3, 147.32), **{"1": "+3V3", "2": "I2C_SCL"})

# --- debug UART (JST-SH 4): 1 GND, 2 3V3, 3 TX (board out), 4 RX (board in) -------------
d.part("J2", "JST_SH_SM04B-SRSS-TB", (76.2, 165.1), **{
    "1": "GND", "2": "+3V3", "3": "UART_TX", "4": "UART_RX"})
d.no_connect("J2", "MP")  # mechanical tab

if __name__ == "__main__":
    out = HERE / "hwlab.kicad_sch"
    d.write(out)
    nets = d.nets()
    print(f"wrote {out.relative_to(HERE.parent)}: {len(d.parts)} parts, {len(nets)} nets")
    for net, pins in sorted(nets.items()):
        if len(pins) < 2:
            print(f"  WARNING single-pin net {net}: {pins}")
