#!/usr/bin/env bash
# FJC Biographical Directory of Article III Federal Judges, 1789-present (export CSVs).
# https://www.fjc.gov/history/judges/biographical-directory-article-iii-federal-judges-export
set -uo pipefail
cd "$(dirname "$0")"
mkdir -p data/raw
failed=0
for f in judges.csv demographics.csv education.csv federal-judicial-service.csv other-federal-judicial-service.csv other-nominations-recess.csv professional-career.csv categories.xlsx; do
  out="data/raw/$f"; [[ -s "$out" ]] && continue
  curl --fail -L --retry 5 -sS -A "Mozilla/5.0 (datapond-maintenance)" -o "$out.part" "https://www.fjc.gov/sites/default/files/history/$f" && mv "$out.part" "$out" && echo "ok $out $(stat -c %s "$out")" || { rm -f "$out.part"; echo "FAIL $out" >&2; failed=$((failed + 1)); }
done
if [[ $failed -gt 0 ]]; then echo "$failed download(s) failed" >&2; exit 1; fi
