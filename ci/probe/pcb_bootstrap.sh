#!/usr/bin/env bash
# One-off: create hardware/hwlab.kicad_pcb from the schematic, place from
# placement.toml, autoroute with Freerouting (stand-in for the owner's GUI
# routing), fill zones, DRC, and upload the board for committing.
set -x
o=$PWD/out
cd hardware
kicad-cli sch export netlist --format kicadsexpr -o /tmp/hwlab.net hwlab.kicad_sch
rm -f hwlab.kicad_pcb
python3 ../tools/pcb_sync.py /tmp/hwlab.net hwlab.kicad_pcb --placement placement.toml || exit 1
cp hwlab.kicad_pcb $o/placed.kicad_pcb
kicad-cli pcb drc --severity-all -o $o/drc-placed.rpt hwlab.kicad_pcb; grep -E "^\[|Found|\*\*" $o/drc-placed.rpt | sort | uniq -c | sort -rn | head -30
kicad-cli pcb render --side top -w 1200 -h 1600 -o $o/placed-top.png hwlab.kicad_pcb
# --- autoroute
t0=$(date +%s)
apt-get update -qq && apt-get install -y -qq openjdk-21-jre-headless curl >/dev/null 2>&1
url=https://github.com/freerouting/freerouting/releases/download/v2.1.0/freerouting-2.1.0.jar
echo "freerouting: $url"; curl -sL -o /tmp/fr.jar "$url"
echo "java+freerouting install $(( $(date +%s) - t0 ))s"
python3 -c "import pcbnew; b=pcbnew.LoadBoard('hwlab.kicad_pcb'); print('dsn', pcbnew.ExportSpecctraDSN(b, '/tmp/hwlab.dsn'))"
t0=$(date +%s)
timeout 900 java -jar /tmp/fr.jar -de /tmp/hwlab.dsn -do /tmp/hwlab.ses -mp 100 --gui.enabled=false 2>&1 | tail -25
echo "freerouting took $(( $(date +%s) - t0 ))s"
cp /tmp/hwlab.dsn /tmp/hwlab.ses $o/ 2>/dev/null
python3 - <<'PY'
import pcbnew
b = pcbnew.LoadBoard('hwlab.kicad_pcb')
print('ses', pcbnew.ImportSpecctraSES(b, '/tmp/hwlab.ses'))
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard('hwlab.kicad_pcb', b)
print('tracks', len(b.GetTracks()))
PY
cp hwlab.kicad_pcb $o/routed.kicad_pcb
kicad-cli pcb drc --severity-all --schematic-parity -o $o/drc-routed.rpt hwlab.kicad_pcb; grep -E "^\[|Found|\*\*" $o/drc-routed.rpt | sort | uniq -c | sort -rn | head -30
kicad-cli pcb render --side top -w 1200 -h 1600 -o $o/routed-top.png hwlab.kicad_pcb
kicad-cli pcb export svg --layers F.Cu,B.Cu,Edge.Cuts,F.SilkS --mode-single -o $o/routed.svg hwlab.kicad_pcb
true
