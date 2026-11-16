# Planted mistakes: agent review verdicts, written BEFORE unblinding

Run 43868914900. Material per code: schematic PDF, netlist, top/bottom renders, copper SVG.
Method: a fixed netlist checklist (decoupling per IC, TX/RX vs pin function, regulator
pinout vs datasheet, inputs left unconnected), then visual comparison of renders.

| code | verdict | evidence |
|------|---------|----------|
| R41 | LDO pinout wrong | U2 pin 3 is 'VO' on +3V3, pin 2 'VI' on VBUS; AMS1117 SOT-223 datasheet: 1 GND, 2 VOUT, 3 VIN |
| R44 | floating pin | U3 pin 12 (CS, input) on an unconnected-() net; LSM6DSO needs CS high for I2C |
| R46 | missing decoupling | 2 ICs on +3V3 (U1, U3) but only one small cap (C3); 19 parts vs 21 elsewhere |
| R64 | clean (control?) | checklist clean; renders look like the reference |
| R69 | TX/RX swapped | net UART_RX on U1 TXD0 (pin 37), UART_TX on RXD0 (pin 36) |
| R92 | VBUS trace too narrow | checklist clean, but the VBUS traces (J1 -> R1 loop -> U2, U2 -> C1) render visibly thinner than R64. Only spotted by side-by-side comparison; not detectable from the netlist |
