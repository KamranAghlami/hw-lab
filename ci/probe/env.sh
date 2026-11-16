#!/usr/bin/env bash
# Inventory of the KiCad image: versions, CLI surface, Python API, tools.
set -x
cat /etc/os-release | head -3
id
kicad-cli version
kicad-cli --help
kicad-cli sch --help
kicad-cli sch export --help
kicad-cli pcb --help
kicad-cli pcb export --help
kicad-cli sch erc --help
kicad-cli pcb drc --help
kicad-cli sch upgrade --help
kicad-cli pcb upgrade --help
kicad-cli pcb render --help
kicad-cli jobset --help
python3 --version
python3 -c "import pcbnew; print(pcbnew.Version()); print([n for n in dir(pcbnew) if 'Specctra' in n or 'Netlist' in n or n.startswith('Load') or n.startswith('Save')])"
which git convert compare rsvg-convert java xvfb-run pip3 2>&1
python3 -m pip --version
ls /usr/share/kicad/ || true
ls /usr/share/kicad/3dmodels 2>/dev/null | head -3
du -sh /usr/share/kicad/* 2>/dev/null
