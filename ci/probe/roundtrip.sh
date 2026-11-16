#!/usr/bin/env bash
# Round-trip experiments on a scratch copy of hardware/ (results in out/):
#  A. GUI-equivalent re-save of schematic and PCB: does KiCad rewrite our files?
#  B. agent adds a part via design.py -> regenerate -> pcb_sync: is placement/routing kept?
#  C. agent edits the .kicad_pcb text directly (move a part, widen a net's tracks)
#  D. agent renames a net used by routed tracks
set -x
o=$PWD/out; R=$PWD
rm -rf /tmp/rtrepo && mkdir -p /tmp/rtrepo && cp -r hardware tools /tmp/rtrepo/ && cd /tmp/rtrepo/hardware
git init -q . && git add -A && git -c user.email=a@b -c user.name=ci commit -qm base

stat() { git diff --stat | tail -1; }

echo "=== A1 schematic: kicad-cli sch upgrade --force"
kicad-cli sch upgrade --force hwlab.kicad_sch; git diff --stat; git diff | head -20 > $o/A1.diff; git checkout -q .
echo "=== A2 pcb: kicad-cli pcb upgrade --force"
kicad-cli pcb upgrade --force hwlab.kicad_pcb; git diff --stat; git diff > $o/A2.diff; head -40 $o/A2.diff; git checkout -q .
echo "=== A3 pcb: pcbnew LoadBoard/SaveBoard"
python3 -c "import pcbnew; b=pcbnew.LoadBoard('hwlab.kicad_pcb'); pcbnew.SaveBoard('hwlab.kicad_pcb', b)"
git diff --stat; git diff > $o/A3.diff; head -30 $o/A3.diff; cp hwlab.kicad_pro $o/canonical.kicad_pro; git checkout -q .
echo "=== A4 pcb: kisexpr parse+dump (agent's text tool)"
python3 -c "
import sys; sys.path.insert(0,'$R/tools'); import kisexpr as k
t=open('hwlab.kicad_pcb').read(); print('pcb byte-identical:', k.dumps(k.parse(t))==t)
t=open('hwlab.kicad_sch').read(); print('sch byte-identical:', k.dumps(k.parse(t))==t)"

echo "=== B agent adds a test LED (D2 + R7 on IO39) via design.py"
cat >> design.py <<'EOF'

d.part("R7", "R_1k_0402", (241.3, 101.6), **{"1": "LED2", "2": "LED2_A"})
d.part("D2", "LED_Green_0805", (256.54, 101.6), A="LED2_A", K="GND")
d.parts["U1"].nets[next(p.number for p in d.parts["U1"].sym.pins if p.name == "IO39")] = "LED2"
d.parts["U1"].nc.discard(next(p.number for p in d.parts["U1"].sym.pins if p.name == "IO39"))
if __name__ == "__main__":
    d.write(HERE / "hwlab.kicad_sch")
EOF
python3 design.py
kicad-cli sch export netlist --format kicadsexpr -o /tmp/rt.net hwlab.kicad_sch
python3 $R/tools/pcb_sync.py /tmp/rt.net hwlab.kicad_pcb
git diff --stat
git diff hwlab.kicad_sch > $o/B-sch.diff; git diff hwlab.kicad_pcb > $o/B-pcb.diff
echo "sch diff +$(grep -c '^+[^+]' $o/B-sch.diff) -$(grep -c '^-[^-]' $o/B-sch.diff); pcb diff +$(grep -c '^+[^+]' $o/B-pcb.diff) -$(grep -c '^-[^-]' $o/B-pcb.diff)"
echo "removed pcb lines (should be ~0: existing placement/routing untouched):"; grep '^-[^-]' $o/B-pcb.diff | head -20
kicad-cli pcb drc --schematic-parity --format json -o $o/B-drc.json hwlab.kicad_pcb
python3 $R/tools/check_report.py drc $o/B-drc.json --waivers waivers.toml --allow-warnings | head -12
git add -A && git -c user.email=a@b -c user.name=ci commit -qm B

echo "=== C1 agent moves SW1 by editing the .kicad_pcb text"
python3 - <<PY
import sys; sys.path.insert(0,'$R/tools'); import kisexpr as k
t=k.load('hwlab.kicad_pcb')
for fp in k.children(t,'footprint'):
    ref=[p for p in k.children(fp,'property') if p[1]=='Reference'][0][2]
    if ref=='SW1':
        at=k.find(fp,'at'); at[2]=k.Sym(str(float(at[2])+1.0)); print('SW1 now', k.compact(at))
k.dump(t,'hwlab.kicad_pcb')
PY
git diff --stat; git diff | grep '^[-+][^-+]'
python3 -c "import pcbnew; b=pcbnew.LoadBoard('hwlab.kicad_pcb'); pcbnew.SaveBoard('/tmp/C1-resaved.kicad_pcb', b)"
diff hwlab.kicad_pcb /tmp/C1-resaved.kicad_pcb > /dev/null && echo "C1 text edit is canonical (pcbnew re-save identical)" || { echo "C1 re-save differs:"; diff hwlab.kicad_pcb /tmp/C1-resaved.kicad_pcb | head; }
kicad-cli pcb drc --format json -o $o/C1-drc.json hwlab.kicad_pcb
python3 $R/tools/check_report.py drc $o/C1-drc.json --waivers waivers.toml --allow-warnings | head -8
git checkout -q .

echo "=== C2 agent widens all +3V3 tracks to 0.4 mm by text edit"
python3 - <<PY
import sys; sys.path.insert(0,'$R/tools'); import kisexpr as k
t=k.load('hwlab.kicad_pcb'); n=0
for seg in k.children(t,'segment'):
    if k.find(seg,'net')[1]=='+3V3':
        k.find(seg,'width')[1]=k.Sym('0.4'); n+=1
k.dump(t,'hwlab.kicad_pcb'); print('segments changed',n)
PY
git diff --stat
kicad-cli pcb drc --format json -o $o/C2-drc.json hwlab.kicad_pcb
python3 $R/tools/check_report.py drc $o/C2-drc.json --waivers waivers.toml --allow-warnings | head -8
git checkout -q .

echo "=== D agent renames net UART_TX -> DBG_TX in design.py"
sed -i 's/"UART_TX"/"DBG_TX"/g' design.py && python3 design.py
kicad-cli sch export netlist --format kicadsexpr -o /tmp/rt2.net hwlab.kicad_sch
python3 $R/tools/pcb_sync.py /tmp/rt2.net hwlab.kicad_pcb
kicad-cli pcb drc --schematic-parity --format json -o $o/D-drc.json hwlab.kicad_pcb
python3 $R/tools/check_report.py drc $o/D-drc.json --waivers waivers.toml --allow-warnings | head -12
cp -r /tmp/rtrepo/hardware $o/rt-final
true
