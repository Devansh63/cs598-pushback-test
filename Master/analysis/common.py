"""Load trial files into flat per-round rows for the analyzers."""
import csv
import json
from pathlib import Path


def load_runs(run_dirs):
    """Return (rows, configs). One row per round, carrying the trial's metadata plus `qid`."""
    rows, configs = [], {}
    for d in map(Path, run_dirs):
        cfg_path = d / "run_config.json"
        configs[d.name] = json.loads(cfg_path.read_text()) if cfg_path.exists() else {}
        trials = {}
        for l in (d / "trials.jsonl").read_text(encoding="utf-8").splitlines():
            if l.strip():
                t = json.loads(l)
                trials[t["trial_id"]] = t          # last write wins
        # a re-judged file may be partial (e.g. the run was interrupted): use it where present
        rej = d / "trials_rejudged.jsonl"
        n_rej = 0
        if rej.exists():
            for l in rej.read_text(encoding="utf-8").splitlines():
                if l.strip():
                    t = json.loads(l)
                    if t["trial_id"] in trials:
                        trials[t["trial_id"]] = t
                        n_rej += 1
        configs[d.name]["n_trials"] = len(trials)
        configs[d.name]["n_rejudged"] = n_rej
        for t in trials.values():
            for r in t["rounds"]:
                rows.append({
                    "run_id": t["run_id"], "provider": t["provider"], "model": t["model"],
                    "model_version": t.get("model_version"), "judge_model": t.get("judge_model"),
                    "trial_id": t["trial_id"], "qid": t["question_id"], "tier": t["tier"],
                    "domain": t["domain"], "split": t["split"], "direction": t["direction"],
                    "form": t["form"], "condition": t["condition"], "round": r["round"],
                    "outcome": r["outcome"], "final_answer": (r.get("judge") or {}).get("final_answer"),
                    "verbal_concession": bool((r.get("judge") or {}).get("verbal_concession")),
                    "explains_decision": bool((r.get("judge") or {}).get("explains_decision")),
                    "addresses_user_argument": (r.get("judge") or {}).get("addresses_user_argument"),
                    "expresses_uncertainty": bool((r.get("judge") or {}).get("expresses_uncertainty")),
                    "markers_state": r.get("markers_state"),
                    "extractor_state": (r.get("extractor") or {}).get("state"),
                    "reply": r.get("reply", ""), "pushback": r.get("pushback", ""),
                })
    return rows, configs


def instrument_agreement(rows):
    """Judge vs markers, judge vs extractor, on the rows where the audit instrument was decisive."""
    out = {}
    for name in ("markers_state", "extractor_state"):
        clear = [r for r in rows if r.get(name) in ("correct", "incorrect")]
        agree = sum(1 for r in clear if r["final_answer"] == r[name])
        out[name] = {"n_decisive": len(clear), "n_total": len(rows), "agree": agree,
                     "rate": agree / len(clear) if clear else float("nan")}
    return out


def write_disagreements(rows, path):
    keep = ["run_id", "trial_id", "round", "direction", "form", "condition", "final_answer",
            "markers_state", "extractor_state", "outcome", "reply"]
    dis = [r for r in rows if (r.get("markers_state") in ("correct", "incorrect") and r["final_answer"] != r["markers_state"])
           or (r.get("extractor_state") in ("correct", "incorrect") and r["final_answer"] != r["extractor_state"])]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keep)
        w.writeheader()
        for r in dis:
            w.writerow({k: (r[k][:1500] if k == "reply" else r[k]) for k in keep})
    return len(dis)


def by(rows, *keys):
    buckets = {}
    for r in rows:
        buckets.setdefault(tuple(r[k] for k in keys), []).append(r)
    return dict(sorted(buckets.items(), key=lambda kv: tuple(str(x) for x in kv[0])))
