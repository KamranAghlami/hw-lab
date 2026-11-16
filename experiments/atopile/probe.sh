#!/usr/bin/env bash
# CI: install atopile and build one of its own example projects, to see what a
# code-first tool emits (PCB vs schematic) and how long it takes.
set -x
o=$PWD/out/atopile; mkdir -p $o
t0=$(date +%s)
apt-get update -qq && apt-get install -y -qq curl ca-certificates >/dev/null
curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null 2>&1
export PATH=$HOME/.local/bin:$PATH
uv tool install --python 3.14 atopile==0.15.9 2>&1 | tail -3
echo "install took $(( $(date +%s) - t0 ))s"
ato --version
ato --help | head -30
git clone -q --depth 1 https://github.com/atopile/atopile /tmp/ato-src
ls /tmp/ato-src/examples | head -30
for ex in esp32_minimal quickstart; do
  [ -d /tmp/ato-src/examples/$ex ] || continue
  cd /tmp/ato-src/examples/$ex; ls
  t0=$(date +%s)
  timeout 900 ato build 2>&1 | tail -40
  echo "ato build $ex exit ${PIPESTATUS[0]} after $(( $(date +%s) - t0 ))s"
  find . -newer /tmp/ato-src/README.md -type f \( -name '*.kicad_*' -o -name '*.net' -o -name '*.csv' -o -name '*.json' \) | grep -v node_modules | head -30 | tee $o/$ex-outputs.txt
  find . -name '*.kicad_sch' | tee -a $o/$ex-outputs.txt
  cd - >/dev/null
  break
done
true
