#!/usr/bin/env bash
# For each schematic under test: ERC, netlist, PDF, and a forced re-save in a
# full copy of the project (= what the GUI would write) diffed against the input.
check() {  # $1 = project dir, $2 = tag
  local dir=$1 tag=$2 o=$PWD/out/$2
  mkdir -p $o
  rm -rf /tmp/p && cp -r $dir /tmp/p
  [ -e /tmp/p/lib ] || cp -r hardware/lib /tmp/p/lib
  for f in hwlab.kicad_pro sym-lib-table fp-lib-table; do [ -e /tmp/p/$f ] || cp hardware/$f /tmp/p/; done
  cd /tmp/p
  echo "===== $tag"
  kicad-cli sch erc --severity-all --format json -o $o/erc.json hwlab.kicad_sch >/dev/null; echo "erc exit $?"
  kicad-cli sch erc --severity-all -o $o/erc.rpt hwlab.kicad_sch >/dev/null; grep -E "^\[|ERC messages" $o/erc.rpt | sort | uniq -c
  kicad-cli sch export netlist --format kicadsexpr -o $o/hwlab.net hwlab.kicad_sch >/dev/null; echo "netlist exit $?"
  kicad-cli sch export pdf -o $o/hwlab.pdf hwlab.kicad_sch >/dev/null; echo "pdf exit $?"
  cp hwlab.kicad_sch $o/input.kicad_sch
  kicad-cli sch upgrade --force hwlab.kicad_sch; echo "upgrade exit $?"
  cp hwlab.kicad_sch $o/resaved.kicad_sch
  diff -u $o/input.kicad_sch $o/resaved.kicad_sch > $o/resave.diff; echo "resave diff lines: $(wc -l < $o/resave.diff)"
  head -60 $o/resave.diff
  cd - >/dev/null
}
check hardware raw-sexpr
[ -f experiments/kiutils/hwlab.kicad_sch ] && check experiments/kiutils kiutils
true
