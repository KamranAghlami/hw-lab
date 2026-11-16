#!/usr/bin/env bash
# CI: SKiDL 3.0 + schematizer -> netlist + KiCad 10 schematic, then ERC/PDF on it.
set -x
o=$PWD/out/skidl; mkdir -p $o
t0=$(date +%s)
apt-get update -qq && apt-get install -y -qq python3-venv >/dev/null
python3 -m venv /tmp/sk && /tmp/sk/bin/pip -q install skidl==3.0.0 schematizer==0.2.0
echo "install took $(( $(date +%s) - t0 ))s"
t0=$(date +%s)
timeout 1500 /tmp/sk/bin/python experiments/skidl/board.py 2>&1 | grep -v "variable is missing" | tail -40
echo "board.py exit ${PIPESTATUS[0]} after $(( $(date +%s) - t0 ))s"
cp -r experiments/skidl/out/. $o/ 2>/dev/null
find experiments/skidl/out -type f | head
sch=$(find experiments/skidl/out -name '*.kicad_sch' | head -1)
if [ -n "$sch" ]; then
  d=$(dirname $sch); cp hardware/sym-lib-table hardware/fp-lib-table $d/ 2>/dev/null; cp -r hardware/lib $d/lib
  kicad-cli sch erc --severity-all -o $o/erc.rpt $sch; grep -E "^\[|ERC messages" $o/erc.rpt | sort | uniq -c
  kicad-cli sch export pdf -o $o/skidl.pdf $sch
fi
