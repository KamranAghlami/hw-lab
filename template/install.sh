#!/usr/bin/env bash
# Copy the hw-lab hardware CI setup into another repo.
#   template/install.sh <target-repo-dir> <board-name> <ghcr-owner-lowercase>
# Copies the tested files from this repo (not a separate copy that could drift) and
# renames board/image identifiers. Review the result, then follow template/README.md.
set -euo pipefail
src=$(cd "$(dirname "$0")/.." && pwd)
dst=${1:?target repo dir}; board=${2:?board name, e.g. tracker}; owner=${3:?ghcr owner, lowercase}
image="ghcr.io/$owner/$board-ci:10.0.8"
mkdir -p "$dst"/{.github/workflows,ci,tools,hardware/lib,firmware/include,docs/memory}
cp "$src"/tools/{kisexpr,schgen,build_lib,pcb_sync,check_report,pinmap,intent_check,sch_overlap,layout_check,stitch_gnd}.py "$dst/tools/"
cp "$src"/ci/Dockerfile "$dst/ci/"
cp "$src"/docs/memory/kicad10-gotchas.md "$dst/docs/memory/"
for f in hardware.yml release.yml ci-image.yml; do
  sed -e "s#ghcr.io/kamranaghlami/hw-lab-ci:10.0.8#$image#g" -e "s#hwlab#$board#g" \
      "$src/.github/workflows/$f" > "$dst/.github/workflows/$f"
done
sed "s/hwlab/$board/g" "$src/hardware/hwlab.kibot.yaml" > "$dst/hardware/$board.kibot.yaml"
cp "$src/hardware/hwlab.kicad_dru" "$dst/hardware/$board.kicad_dru"
sed "s/\"hwlab.kicad_pro\"/\"$board.kicad_pro\"/" "$src/hardware/hwlab.kicad_pro" > "$dst/hardware/$board.kicad_pro"
for f in sym-lib-table fp-lib-table; do sed -e "s/hwlab/$board/g" -e "s/hw-lab/$board/g" "$src/hardware/$f" > "$dst/hardware/$f"; done
printf '# Reviewed ERC/DRC waivers (tools/check_report.py). Each needs a reason.\n' > "$dst/hardware/waivers.toml"
[ -e "$dst/hardware/lib/parts.toml" ] || { sed -n '1,/^\[\[part\]\]/p' "$src/hardware/lib/parts.toml" | sed '$d' | sed "s/hwlab/$board/g"; printf '\n[library]\nname = "%s"\n' "$board"; } > "$dst/hardware/lib/parts.toml"
echo "installed into $dst (board=$board, image=$image). Next: template/README.md"
