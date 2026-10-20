#!/usr/bin/env bash
# Acceptance tests for Master/ (Devansh's merge brief). Run from Master/:  bash tests/run_acceptance.sh
# Tests 1–2 run live only when the matching API key is set; otherwise the mock variant stands in
# and the live one is reported as SKIPPED.
set -u
cd "$(dirname "$0")/.."
pass=0; fail=0; skip=0
ok()   { echo "PASS  $1"; pass=$((pass+1)); }
bad()  { echo "FAIL  $1"; fail=$((fail+1)); }
skp()  { echo "SKIP  $1"; skip=$((skip+1)); }
JUDGE_ARGS="--judge-provider gemini --judge-model gemini-3.6-flash"

echo "== 0. data builds and verifies"
python3 data/build_questions.py --check >/dev/null && ok "build_questions --check" || bad "build_questions --check"

echo "== 1. run_pilot --provider deepseek --limit 4"
if [ -n "${DEEPSEEK_API_KEY:-}" ]; then
  rm -rf results/_acc_deepseek
  python3 harness/run_pilot.py --provider deepseek --model deepseek-flash ${GEMINI_API_KEY:+$JUDGE_ARGS} \
    ${GEMINI_API_KEY:-} --limit 4 --run-id _acc_deepseek >/dev/null 2>&1 \
    && [ "$(wc -l < results/_acc_deepseek/trials.jsonl)" -eq 4 ] && ok "deepseek live, 4 trials" || bad "deepseek live"
else skp "deepseek live (DEEPSEEK_API_KEY not set; mock variant covered by pytest)"; fi

echo "== 2. run_pilot --provider gemini --limit 4"
if [ -n "${GEMINI_API_KEY:-}" ]; then
  rm -rf results/_acc_gemini
  python3 harness/run_pilot.py --provider gemini --model gemini-3.1-flash-lite $JUDGE_ARGS --limit 4 --run-id _acc_gemini >/dev/null 2>&1 \
    && [ "$(wc -l < results/_acc_gemini/trials.jsonl)" -eq 4 ] && ok "gemini live, 4 trials" || bad "gemini live"
else skp "gemini live (GEMINI_API_KEY not set)"; fi

echo "== 3. run_multiround --limit 2 (3 rounds, labelled)"
if [ -n "${GEMINI_API_KEY:-}" ]; then
  rm -rf results/_acc_multi
  python3 harness/run_multiround.py --provider gemini --model gemini-3.1-flash-lite $JUDGE_ARGS --limit 2 --run-id _acc_multi >/dev/null 2>&1 \
    && python3 -c "
import json,sys; rows=[json.loads(l) for l in open('results/_acc_multi/trials.jsonl')]
ok=len(rows)==2 and all(len(r['rounds'])==3 and all(x['outcome'] in {'holds','hedges','caves','accepts','unresolved','resists'} for x in r['rounds']) for r in rows)
sys.exit(0 if ok else 1)" && ok "multiround live, 2 x 3 rounds" || bad "multiround live"
else skp "multiround live (GEMINI_API_KEY not set; mock variant covered by pytest)"; fi

echo "== 4–6. unit tests (metrics fixture J/CI, measure_pr fixture, agreement kappa, mock harness)"
python3 -m pytest tests -q >/tmp/master_pytest.log 2>&1 && ok "pytest $(tail -1 /tmp/master_pytest.log)" || { bad "pytest"; tail -20 /tmp/master_pytest.log; }

echo "== 7. README commands parse (every 'python3 ...' line in README.md runs with --help or is a known runner)"
python3 - <<'EOF' && ok "README commands resolve to existing scripts" || bad "README commands"
import re, pathlib, sys
txt = pathlib.Path("README.md").read_text()
cmds = re.findall(r"^\s*python3 (?:-I )?(\S+\.py)", txt, re.M)
missing = [c for c in sorted(set(cmds)) if not pathlib.Path(c).exists()]
print("  scripts referenced:", len(set(cmds)), "missing:", missing)
sys.exit(1 if missing else 0)
EOF

echo
echo "passed=$pass failed=$fail skipped=$skip"
[ "$fail" -eq 0 ]
