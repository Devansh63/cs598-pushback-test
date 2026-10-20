"""Multi-round persistence: one pushback form, then fixed escalation rounds; every reply is judged.

  python3 harness/run_multiround.py --provider gemini --model gemini-3.1-flash-lite \
      --judge-provider gemini --judge-model gemini-3.6-flash --forms scripted --limit 2

Same trial schema as run_pilot.py; `rounds[]` has one entry per round. The condition's system
extra (and any verification) is computed once from round 1 and held constant across rounds.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from harness import lib  # noqa: E402
from harness.judge import judge_reply  # noqa: E402
from harness.run_pilot import condition_extra, plan_trials  # noqa: E402
from providers.base import get_provider  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--judge-provider", default="gemini")
    ap.add_argument("--judge-model", required=True)
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--tiers", default="easy,hard")
    ap.add_argument("--splits", default="dev,heldout")
    ap.add_argument("--forms", default="scripted,real")
    ap.add_argument("--conditions", default="none")
    ap.add_argument("--directions", default="user_wrong,user_right")
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--run-id")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--no-extractor", action="store_true")
    a = ap.parse_args(argv)

    provider = get_provider(a.provider)
    judge = provider if (a.judge_provider == a.provider) else get_provider(a.judge_provider)
    forms = lib.load_forms()
    escalation = forms["escalation"][: max(0, a.rounds - 1)]
    qs = lib.load_questions(tiers=a.tiers.split(","), splits=a.splits.split(","))
    conditions = [c for c in a.conditions.split(",") if c != "no_pushback"]
    trials = plan_trials(qs, forms, a.forms.split(","), a.directions.split(","), conditions)
    if a.limit:
        trials = trials[: a.limit]
    run_id = a.run_id or f"multiround_{a.provider}_{a.model}"
    d = lib.run_dir(run_id)
    lib.write_config(d, {
        "kind": "multi_round", "run_id": run_id, "provider": a.provider, "model": a.model,
        "temperature": a.temperature, "judge_provider": a.judge_provider, "judge_model": a.judge_model,
        "tiers": a.tiers, "splits": a.splits, "forms": a.forms, "conditions": a.conditions,
        "directions": a.directions, "rounds": 1 + len(escalation), "escalation": escalation,
        "n_trials_planned": len(trials), "seed": "n/a (temperature 0)",
        "forms_file": "data/pushback_forms_v1.json", "questions_file": "data/questions_v1.jsonl"})
    path = d / "trials.jsonl"
    done = lib.load_jsonl(path)
    todo = [t for t in trials if t["trial_id"] not in done]
    print(f"{run_id}: {len(trials)} trials planned, {len(done)} done, {len(todo)} to run "
          f"({1 + len(escalation)} rounds each)")

    def work(t):
        q = t["q"]
        extra, verification, predicted = condition_extra(provider, a.model, t, forms)
        turns, rounds, version = [], [], None
        pushbacks = [t["pushback"]] + [e.format(claim=t["claim"]) for e in escalation]
        for i, push in enumerate(pushbacks, 1):
            turns.append(("user", push))
            history = lib.build_messages(q, t["initial_answer"], turns, extra=extra)
            reply, meta = provider.chat(history, model=a.model, temperature=a.temperature)
            version = meta["model_version"]
            res = judge_reply(judge, a.judge_model, q, history, reply, t["claim"], t["direction"],
                              with_extractor=not a.no_extractor)
            rounds.append(dict(round=i, pushback=push, reply=reply, finish_reason=meta["finish_reason"], **res))
            turns.append(("assistant", reply))
        row = {k: t[k] for k in ("trial_id", "question_id", "tier", "domain", "split", "direction",
                                 "form", "condition", "claim", "initial_answer")}
        row.update(run_id=run_id, provider=a.provider, model=a.model, model_version=version,
                   temperature=a.temperature, judge_provider=a.judge_provider, judge_model=a.judge_model,
                   system_extra=extra, verification=verification, predicted_type=predicted,
                   rounds=rounds, ts=lib.now())
        lib.append_jsonl(path, row)

    errors = lib.run_parallel(work, todo, a.workers, "trial")
    print(f"done; {errors} errors; usage {provider.usage.summary()}; log {path}")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
