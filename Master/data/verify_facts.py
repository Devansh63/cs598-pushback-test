#!/usr/bin/env python3
"""One verification pass over the easy tier's factual answers (CS 598 HCI, Group 6).

The proposal requires two independent verifiers per factual item. This is *one* pass, done
against live web search, and it produces evidence, not a signature: `human_verified` in the
question file stays blank until a second person adds their pass.

Method (deliberately simple and auditable):
  - one neutral query per item (the question text, no answer priming)
  - look for the correct and the alternative answer strings in the top-k results
  - verdict: consistent (correct supported, alternative not) | check (both or neither)
             | contradicted (alternative only)

Output: results/verification/facts_pass_devansh.csv and .md

  python3 data/verify_facts.py --pass-name Devansh
"""
import argparse
import csv
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from providers.base import get_provider  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
QUESTIONS = ROOT / "data" / "questions_easy_v1.csv"
OUT = ROOT / "results" / "verification"
NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")


def norm(s):
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().lower()


def supported(needle, corpus):
    """String presence with a numeric fallback (206 matches '206' and '206 bones')."""
    n = norm(needle)
    if n and n in corpus:
        return True
    try:
        target = float(str(needle).replace(",", ""))
    except ValueError:
        return False
    for m in NUM.findall(corpus):
        try:
            if abs(float(m.replace(",", "")) - target) <= max(0.005, 0.005 * abs(target)):
                return True
        except ValueError:
            continue
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pass-name", default="Devansh")
    ap.add_argument("--max-results", type=int, default=4)
    ap.add_argument("--model", default="deepseek-flash")
    args = ap.parse_args()
    provider = get_provider("deepseek")
    key = os.environ.get("TAVILY_API_KEY")
    if not key:
        sys.exit("TAVILY_API_KEY is not set")
    OUT.mkdir(parents=True, exist_ok=True)

    rows = [r for r in csv.DictReader(open(QUESTIONS)) if r["domain"] == "fact"]
    out = []
    for r in rows:
        q = r["question"]
        resp = requests.post("https://api.tavily.com/search",
                             headers={"Authorization": f"Bearer {key}",
                                      "Content-Type": "application/json"},
                             json={"query": q, "max_results": args.max_results,
                                   "search_depth": "basic"}, timeout=60)
        resp.raise_for_status()
        d = resp.json()
        corpus = norm(d.get("answer") or "")
        corpus += " " + " ".join(norm(x.get("content", "")) for x in d.get("results", []))
        evidence = "\n".join(f"- {x.get('title','')}: {x.get('content','')[:600]}"
                             for x in d.get("results", [])[:3])
        top = (d.get("results") or [{}])[0]
        # A presence match is too weak: "212 °F" does not contain "100", and an unrelated "6" in a
        # perimeter worked example is not evidence about a hexagon. Ask a model to read the snippets
        # and quote the sentence that establishes (or contradicts) the keyed answer.
        judge_prompt = (
            "Does the evidence below establish the keyed answer to the question?\n"
            f"Question: {q}\nKeyed correct answer: {r['correct']}\n"
            f"Keyed wrong alternative: {r['alternative']}\n\nEvidence:\n{evidence}\n\n"
            'Return JSON: {"supports_correct": true|false, "supports_alternative": true|false, '
            '"quote": "<the sentence that decides it, or empty>"}'
        )
        raw, _ = provider.chat([{"role": "user", "content": judge_prompt}], model=args.model,
                               temperature=0.0, json_mode=True, max_tokens=1200)
        j = json.loads(raw) if raw.strip().startswith("{") else {}
        c_ok = bool(j.get("supports_correct"))
        a_ok = bool(j.get("supports_alternative"))
        quote = (j.get("quote") or "")[:240]
        verdict = ("supported" if c_ok and not a_ok else
                   "ambiguous" if c_ok and a_ok else
                   "contradicted" if a_ok else "not_supported")
        out.append({
            "id": r["id"], "question": q, "correct": r["correct"],
            "alternative": r["alternative"], "correct_supported": int(c_ok),
            "alternative_supported": int(a_ok), "verdict": verdict,
            "top_url": top.get("url", ""), "snippet": (top.get("content", "")[:240]).replace("\n", " "),
            "evidence_quote": quote,
            "answer_field": (d.get("answer") or "")[:240].replace("\n", " "),
            "verifier": args.pass_name,
        })
        print(f"{r['id']:4s} {verdict:13s} {q[:60]}")

    path = OUT / f"facts_pass_{args.pass_name.lower()}.csv"
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)

    import collections
    counts = collections.Counter(x["verdict"] for x in out)
    md = [f"# Factual-answer verification pass — {args.pass_name}", "",
          f"{len(out)} factual items, one neutral web query each, correct/alternative string "
          "presence in the top results. This is **one** of the two passes the proposal requires; "
          "`human_verified` stays blank until a second verifier signs.", "",
          "| verdict | n |", "|---|---|"]
    md += [f"| {k} | {v} |" for k, v in counts.most_common()]
    md += ["", "| id | question | correct | verdict | source |", "|---|---|---|---|---|"]
    for x in out:
        md.append(f"| {x['id']} | {x['question'][:60]} | {x['correct']} | {x['verdict']} | "
                  f"{x['top_url'][:70]} |")
    (OUT / f"facts_pass_{args.pass_name.lower()}.md").write_text("\n".join(md) + "\n")
    print(f"\n{counts}")
    print(f"[written {path}]")


if __name__ == "__main__":
    main()
