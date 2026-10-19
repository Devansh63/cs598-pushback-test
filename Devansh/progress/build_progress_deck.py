#!/usr/bin/env python3
"""Build the pilot-results deck (Group 6, CS 598 HCI).

Insert-ready slides reporting what was actually run. Reuses the layout helpers from
Midterm/build_deck.py so the visual system matches the midterm deck.

Run: python3 build_progress_deck.py -> Progress_Slides.pptx
"""
import os
import sys

from pptx import Presentation

HERE = os.path.dirname(os.path.abspath(__file__))
MIDTERM = os.path.join(os.path.dirname(HERE), "Midterm")
sys.path.insert(0, MIDTERM)

import build_deck as bd  # noqa: E402

TEMPLATE = os.path.join(os.path.dirname(HERE), "Illinois PowerPoint Template 1.pptx")
OUT = os.path.join(HERE, "Progress_Slides.pptx")
I = bd.Inches


def build():
    prs = Presentation(TEMPLATE)
    bd.blank(prs)

    # ---- 1 title
    s = prs.slides.add_slide(bd.layout(prs, "TITLE_ONLY"))
    for ph in list(s.placeholders):
        ph._element.getparent().remove(ph._element)
    from pptx.enum.shapes import MSO_SHAPE
    band = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, bd.SW, I(2.35))
    band.fill.solid(); band.fill.fore_color.rgb = bd.ILLINI_BLUE
    band.line.fill.background(); band.shadow.inherit = False
    stripe = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, I(2.35), bd.SW, I(0.09))
    stripe.fill.solid(); stripe.fill.fore_color.rgb = bd.ILLINI_ORANGE
    stripe.line.fill.background(); stripe.shadow.inherit = False

    tf = bd.textbox(s, I(0.7), I(0.55), I(11.9), I(0.8))
    p = tf.paragraphs[0]; p.text = "Pilot results: what we ran"
    for r in p.runs:
        r.font.size, r.font.bold, r.font.color.rgb = bd.Pt(38), True, bd.RGBColor(0xFF, 0xFF, 0xFF)
    tf = bd.textbox(s, I(0.7), I(1.42), I(11.9), I(0.6))
    p = tf.paragraphs[0]
    p.text = "What we ran, what came back, and what it changes"
    for r in p.runs:
        r.font.size, r.font.color.rgb = bd.Pt(17), bd.RGBColor(0xE6, 0xEA, 0xF2)
    tf = bd.textbox(s, I(0.7), I(2.9), I(11.9), I(2.0))
    for i, line in enumerate([
        "Progress since the proposal",
        "Group 6 \u00b7 CS 598 HCI",
        "Devansh Agrawal \u00b7 Zhongyin Wang \u00b7 Sahil Sashi \u00b7 Mathew Pan \u00b7 Xuejun Zhang \u00b7 Zoey Yao",
    ]):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = line; p.space_after = bd.Pt(7)
        for r in p.runs:
            r.font.size = bd.Pt(16 if i < 2 else 14)
            r.font.bold = i == 0
            r.font.color.rgb = bd.ILLINI_BLUE if i == 0 else bd.GREY
    bd.notes(s, "Everything on the following slides is already run and logged. All artifacts are in "
                "the Progress folder; every number is reproducible from the scripts listed at the end.")

    # ---- 2 what was built
    s = bd.add(prs, "What we actually built and ran")
    bd.table(s, ["Artifact", "Scale"], [
        ["Question set with verified answers + plausible wrong alternative",
         "60 items: 30 math (answers recomputed from expressions, 0 failures), 30 factual"],
        ["Pushback stimuli, both directions, four forms",
         "480 texts = 60 questions \u00d7 2 directions \u00d7 (3 reconstructed + scripted)"],
        ["RQ2 trials (no intervention)",
         "960 = 2 models \u00d7 4 forms \u00d7 2 directions \u00d7 60 questions"],
        ["RQ3 trials (4 conditions)",
         "1,440 = 4 conditions \u00d7 3 forms \u00d7 2 directions \u00d7 60 questions"],
        ["Multi-turn escalation arm",
         "240 conversations \u00d7 3 escalating pushback rounds = 720 replies"],
        ["Total across all runs", "~9,600 model calls, ~$1.00; the main pilot alone was 4,421 calls / $0.48 in 8 minutes"],
    ], top=I(1.5), fsize=12, hsize=12)
    bd.takeaway(s, "Fully resumable: every trial is appended to a JSONL log, so an interrupted run "
                   "continues where it stopped.")
    bd.notes(s, "Lead with scale and reproducibility. The point is that the pipeline exists and "
                "produces auditable data, not that the results are final.")

    # ---- 3 RQ2
    s = bd.add(prs, "RQ2: how the two models respond")
    bd.table(s, ["Model", "Pushback form", "Cave \\| user wrong", "Accept \\| user right", "J"], [
        ["flash", "factual_correction", "1.7%  [0, 9]", "98.3%", "+95.0"],
        ["flash", "clarification_demand", "5.0%  [2, 14]", "95.0%", "+90.0"],
        ["flash", "emotional_pushback", "5.0%  [2, 14]", "98.3%", "+93.3"],
        ["flash", "scripted", "3.3%  [1, 11]", "96.7%", "+91.7"],
        ["pro", "factual_correction", "1.7%  [0, 9]", "98.3%", "+95.0"],
        ["pro", "clarification_demand", "1.7%  [0, 9]", "98.3%", "+95.0"],
        ["pro", "emotional_pushback", "5.0%  [2, 14]", "95.0%", "+90.0"],
        ["pro", "scripted", "1.7%  [0, 9]", "98.3%", "+93.3"],
    ], top=I(1.5), fsize=11.5, hsize=11)
    bd.bullets(s, [
        "n = 120 per cell. J = P(hold | user wrong) + P(accept | user right) \u2212 1; 0 is chance.",
        "Caving is rare in this design, and accepting a valid correction is near ceiling.",
    ], top=I(5.3), size=13, space=6)
    bd.notes(s, "Interval is a Wilson 95% interval. Do not describe these as final: they are a pilot "
                "with 60 questions and one vendor's models.")

    # ---- 4 two findings from RQ2
    s = bd.add(prs, "Two things the pilot already shows")
    bd.bullets(s, [
        ("Task type dominates pushback form.", 0, True),
        ("Every caving event came from factual-knowledge items. Arithmetic the model can verify "
         "by computation was immune: 0.0% caving for both models on math, 7.8% and 5.6% on facts.", 1),
        ("Scripted pushback did not misestimate caving.", 0, True),
        ("Reconstructed vs scripted, paired over questions: flash \u22121.7 pp [\u22126, 3], "
         "pro \u22120.8 pp [\u22123, 2]. Both intervals span zero. Our original motivating gap "
         "\u2014 \u201cscripted pushback hides the real problem\u201d \u2014 is not reproduced "
         "here.", 1),
        ("What that means for the framing.", 0, True),
        ("The difference between lab and real pushback may be about context and history, not "
         "about wording. That is a sharper and more useful question than the one we proposed.", 1),
    ], top=I(1.45), size=15, space=11)
    bd.notes(s, "This is the honest version: our own hypothesis did not survive. Say it plainly, "
                "then say what replaced it.")

    # ---- 5 RQ3
    s = bd.add(prs, "RQ3: does type-aware guidance add anything?")
    bd.table(s, ["Condition", "Cave \\| user wrong", "Accept \\| user right", "J"], [
        ["none", "3.9%", "97.2%", "+92.8"],
        ["reframe (published fix)", "8.9%", "93.3%", "+82.8"],
        ["verify_only", "2.2%", "96.7%", "+94.4"],
        ["verify_type (ours)", "1.7%", "97.8%", "+95.6"],
    ], top=I(1.5), fsize=12, hsize=12)
    bd.bullets(s, [
        ("Pre-registered contrast, verify_type vs verify_only:", 0, True),
        ("cave \u22120.8 pp [\u22122, 1], good outcome +0.6 pp [\u22121, 2]. Null. We can rule out "
         "a gain larger than about 2 pp \u2014 and with caving already at 2%, there was little "
         "room.", 1),
        ("The unexpected result: question reframing made things worse.", 0, True),
        ("+3.9 pp caving [1, 7], good outcome \u22125.0 pp [\u22128, \u22122]. Mechanism is visible "
         "in the transcripts: the model restates the user's wrong claim as a question and then "
         "answers from that premise. Contradicts the published benefit in a setting closer to real "
         "use.", 1),
    ], top=I(3.7), size=14, space=9)
    bd.notes(s, "Be careful and precise: this is one prompt instantiation, not a refutation of Dubois "
                "et al. But it is directly relevant to anyone deploying the fix.")

    # ---- 6 multiturn
    s = bd.add(prs, "Does caving accumulate? No.")
    bd.table(s, ["Model", "After push 1", "After push 2", "After push 3", "Accept after 3"], [
        ["flash", "1.7%", "1.7%", "3.3%", "98.3%"],
        ["pro", "3.3%", "3.3%", "3.3%", "98.3%"],
    ], top=I(1.6), fsize=13, hsize=13)
    bd.bullets(s, [
        "240 conversations, three escalating pushbacks each, claim held constant "
        "(counter-assertion \u2192 basis challenge \u2192 frustration).",
        "The curve is flat. Repeated pressure does not produce caving on short verifiable answers, "
        "which rules out \u201cone turn is too weak\u201d as the explanation for the floor.",
        "What is left: supplying the initial answer as history anchors the model, and the items are "
        "unambiguous, so there is a strongly represented correct answer to fall back on.",
    ], top=I(3.3), size=14.5, space=10)
    bd.takeaway(s, "Caving here is a design artifact, not a model property. Next iteration changes the "
                   "design, not the sample size.")
    bd.notes(s, "This is the most important slide for planning: it tells us where not to spend the "
                "remaining weeks.")

    # ---- 7 instruments
    s = bd.add(prs, "Can we trust the numbers? Instrument checks")
    bd.table(s, ["Instrument", "Result", "Consequence"], [
        ["Verification call vs answer key", "99.6% (717/720)", "the verification component works"],
        ["Answer-state detector vs extractor", "91.7% (110/120)", "109 labels were re-derived; "
                                                                  "extractor label used"],
        ["Classifier on our stimuli", "100%", "trivial \u2014 the stimuli came from templates"],
        ["Classifier on real pushback", "55.9% (33/59)", "clarification recall only 35%: "
                                                           "type-aware arm rests on a weak detector"],
    ], top=I(1.5), fsize=12, hsize=12)
    bd.takeaway(s, "The uncomfortable one is the last row. Any claim about type-awareness has to carry "
                   "that caveat.")
    bd.notes(s, "Volunteer the classifier weakness before someone finds it. It is the cleanest evidence "
                "that we are testing our instruments, not just our hypotheses.")

    # ---- 8 phase 1
    s = bd.add(prs, "Phase 1: the lexical filter we proposed recovers 2% of pushback")
    bd.table(s, ["Quantity", "Estimate", "95% CI"], [
        ["Precision (candidates that are genuine pushback)", "58.0%", "[50.0, 65.6]"],
        ["Recall (genuine pushback the filter retrieves)", "2.0%", "[0.7, 5.7]"],
        ["Candidate yield", "4.2 per 1,000 English pairs", "\u2014"],
        ["Implied prevalence of genuine pushback", "~12.2% of pairs", "\u2014"],
    ], top=I(1.5), fsize=12, hsize=12)
    bd.bullets(s, [
        "Measured on 60,000 conversations (34,800 English, 37,857 usable assistant\u2192user pairs).",
        "Pushback is common but lexically invisible: about one pair in eight is a genuine challenge, "
        "and the cue suite finds one in fifty.",
        "Our earlier 20.7% figure was recall measured inside a set already known to be pushback \u2014 "
        "an optimistic ceiling. Against the open corpus the same idea performs at 2%.",
        "Cue precision varies from 100% (\"that's wrong\", n=5) to 37% (\"incorrect\", n=59). If we keep "
        "a lexical pass, cues must be weighted, and a semantic stage must do the rest.",
    ], top=I(3.55), size=13.5, space=8)
    bd.notes(s, "This is the finding that changes Phase 1. It is also the strongest example of the "
                "methodology the review asked for: measure the instrument before trusting the data.")

    # ---- 9 what changes
    s = bd.add(prs, "What this changes in the remaining weeks")
    bd.bullets(s, [
        ("1. Phase 1 becomes semantic retrieval plus human coding.", 0, True),
        ("A weighted lexical pre-filter at 58% precision can seed candidates, but it cannot be "
         "the sampling strategy. Recall at 2% would make the corpus a biased slice.", 1),
        ("2. The pushback experiment needs a harder design, not more trials.", 0, True),
        ("Natural-context replay with model-generated answers, and items where the plausible "
         "wrong answer is genuinely attractive. The supplied-history design is at the floor.", 1),
        ("3. Validate the classifier before claiming type-awareness.", 0, True),
        ("At 55.9% on real pushback, the type label is closer to noise than signal. Either improve "
         "it or drop the type-aware arm to a mechanism study.", 1),
        ("4. Treat published fixes as hypotheses.", 0, True),
        ("Question reframing degraded performance in our implementation. That is worth reporting "
         "and worth understanding \u2014 it is a finding, not a problem with our setup.", 1),
    ], top=I(1.4), size=14, space=10)
    bd.notes(s, "Close on decisions, not on numbers. Each bullet is something we will do differently "
                "because of evidence we generated this week.")

    prs.save(OUT)
    print(f"saved {OUT}")
    print(f"slides: {len(prs.slides)}")


if __name__ == "__main__":
    build()
