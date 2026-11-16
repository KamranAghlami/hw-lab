#!/usr/bin/env bash
# ERC + forced re-save (= what a GUI save would write) + netlist/PDF of hardware/hwlab.kicad_sch
cd hardware
cp hwlab.kicad_sch ../out/generated.kicad_sch
kicad-cli sch erc --severity-all --format json -o ../out/erc.json hwlab.kicad_sch; echo "erc exit $?"
kicad-cli sch erc --severity-all -o ../out/erc.rpt hwlab.kicad_sch; cat ../out/erc.rpt | head -80
kicad-cli sch export netlist --format kicadsexpr -o ../out/hwlab.net hwlab.kicad_sch; echo "netlist exit $?"
kicad-cli sch export pdf -o ../out/hwlab.pdf hwlab.kicad_sch; echo "pdf exit $?"
cp hwlab.kicad_sch /tmp/resave.kicad_sch
cp hwlab.kicad_pro sym-lib-table /tmp/ ; mkdir -p /tmp/lib && cp lib/hwlab.kicad_sym /tmp/lib/
kicad-cli sch upgrade --force /tmp/resave.kicad_sch; echo "upgrade exit $?"
cp /tmp/resave.kicad_sch ../out/resaved.kicad_sch
diff -u hwlab.kicad_sch /tmp/resave.kicad_sch > ../out/resave.diff; echo "diff lines: $(wc -l < ../out/resave.diff)"
head -150 ../out/resave.diff
