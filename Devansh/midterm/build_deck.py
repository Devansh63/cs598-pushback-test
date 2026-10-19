#!/usr/bin/env python3
"""Build the Group 6 (CS 598 HCI) midterm deck from the official Illinois template.

Run:  python3 build_deck.py     ->  Group6_Midterm_Slides.pptx
Deps: python-pptx

All quantitative content comes from reanalysis.md / reanalysis.json, produced by
prelim_analysis.py. Slides containing [[FILL: ...]] need group input before presenting.
"""
import copy
import json
import os
import sys

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Emu, Inches, Pt

HERE = os.path.dirname(os.path.abspath(__file__))
def resolve_template(name="Illinois PowerPoint Template 1.pptx"):
    """Find the course template without hard-coding one machine's layout.

    Order: ILLINOIS_TEMPLATE env var, Devansh/assets/, the course folder, then the
    previously built deck (which carries the same theme and layouts).
    """
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.environ.get("ILLINOIS_TEMPLATE"),
        os.path.join(os.path.dirname(here), "assets", name),
        os.path.join(here, name),
        os.path.expanduser("~/CS 598 HCI/" + name),
        "/Users/devanshagrawal/CS 598 HCI/" + name,
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return None

TEMPLATE = os.path.join(os.path.dirname(HERE), "Illinois PowerPoint Template 1.pptx")
OUTPUT = os.path.join(HERE, "Group6_Midterm_Slides.pptx")

ILLINI_BLUE = RGBColor(0x13, 0x29, 0x4B)
ILLINI_ORANGE = RGBColor(0xE8, 0x4A, 0x27)
GREY = RGBColor(0x50, 0x50, 0x50)
BODY = RGBColor(0x22, 0x22, 0x22)

SW, SH = Inches(13.3333), Inches(7.5)
LEFT, WIDTH = Inches(0.62), Inches(12.09)


# ---------------------------------------------------------------- helpers
def blank(prs):
    """Strip the template's 22 sample slides."""
    sld_ids = prs.slides._sldIdLst
    for sid in list(sld_ids):
        prs.part.drop_rel(sid.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"))
        sld_ids.remove(sid)


def layout(prs, name, fallback=0):
    for lay in prs.slide_layouts:
        if lay.name.strip().lower() == name.strip().lower():
            return lay
    return prs.slide_layouts[fallback]


def add(prs, title, layout_name="TITLE_ONLY"):
    slide = prs.slides.add_slide(layout(prs, layout_name))
    for ph in list(slide.placeholders):
        if ph.placeholder_format.idx != 0:
            ph._element.getparent().remove(ph._element)
    t = slide.shapes.title
    if t is not None:
        t.left, t.top, t.width, t.height = LEFT, Inches(0.34), WIDTH, Inches(0.92)
        t.text_frame.text = title
        for p in t.text_frame.paragraphs:
            for r in p.runs:
                r.font.size = Pt(28)
                r.font.bold = True
                r.font.color.rgb = ILLINI_BLUE
    return slide


def textbox(slide, left, top, width, height):
    tb = slide.shapes.add_textbox(left, top, width, height)
    tf = tb.text_frame
    tf.word_wrap = True
    return tf


def _bullet_char(p, char="\u2022", marL=Inches(0.24), indent=Inches(-0.24)):
    pPr = p._p.get_or_add_pPr()
    pPr.set("marL", str(int(marL)))
    pPr.set("indent", str(int(indent)))
    for tag in ("a:buNone", "a:buChar", "a:buAutoNum"):
        for el in pPr.findall("{http://schemas.openxmlformats.org/drawingml/2006/main}" + tag.split(":")[1]):
            pPr.remove(el)
    from pptx.oxml.ns import qn
    pPr.append(pPr.makeelement(qn("a:buChar"), {"char": char}))


def bullets(slide, items, top=Inches(1.42), left=LEFT, width=WIDTH, height=None,
            size=15, space=8, colour=BODY):
    """items: str, or (str, level) or (str, level, bold)."""
    tf = textbox(slide, left, top, width, height or (SH - top - Inches(0.5)))
    first = True
    for item in items:
        text, level, bold = (item, 0, False) if isinstance(item, str) else (
            item + (False,) * (3 - len(item)) if len(item) < 3 else item)
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.text = text
        p.level = level
        p.space_after = Pt(space)
        if level == 0:
            _bullet_char(p, "\u2022", Inches(0.26 + 0.3 * level), Inches(-0.26))
        else:
            _bullet_char(p, "\u2013", Inches(0.26 + 0.3 * level), Inches(-0.22))
        for r in p.runs:
            r.font.size = Pt(size - (1 if level else 0))
            r.font.bold = bold
            r.font.color.rgb = colour
    return tf


def table(slide, header, rows, left=LEFT, top=Inches(1.5), width=WIDTH,
          height=Inches(0.4), fsize=11, hsize=11):
    shape = slide.shapes.add_table(len(rows) + 1, len(header), left, top, width, height)
    tbl = shape.table
    tbl.first_row = True
    for c, head in enumerate(header):
        cell = tbl.cell(0, c)
        cell.text = head
        for p in cell.text_frame.paragraphs:
            for r in p.runs:
                r.font.size = Pt(hsize)
                r.font.bold = True
                r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        cell.fill.solid()
        cell.fill.fore_color.rgb = ILLINI_BLUE
    for ri, row in enumerate(rows, start=1):
        for ci, val in enumerate(row):
            cell = tbl.cell(ri, ci)
            cell.text = str(val)
            cell.margin_left = cell.margin_right = Inches(0.06)
            for p in cell.text_frame.paragraphs:
                for r in p.runs:
                    r.font.size = Pt(fsize)
                    r.font.color.rgb = BODY
    return tbl


def notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text


def takeaway(slide, text, top=None):
    tf = textbox(slide, LEFT, top or Inches(6.35), WIDTH, Inches(0.75))
    p = tf.paragraphs[0]
    p.text = text
    for r in p.runs:
        r.font.size = Pt(13)
        r.font.bold = True
        r.font.color.rgb = ILLINI_ORANGE


# ---------------------------------------------------------------- build
def build():
    base = resolve_template()
    if base is None and os.path.exists(OUT):
        base = OUT  # reuse the built deck: same theme and layouts
    if base is None:
        sys.exit("template not found; set ILLINOIS_TEMPLATE to the course template")
    prs = Presentation(base)
    blank(prs)

    # ---- 1 title
    s = prs.slides.add_slide(layout(prs, "TITLE_ONLY"))
    for ph in list(s.placeholders):
        ph._element.getparent().remove(ph._element)
    band = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SW, Inches(2.35))
    band.fill.solid()
    band.fill.fore_color.rgb = ILLINI_BLUE
    band.line.fill.background()
    band.shadow.inherit = False
    stripe = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, Inches(2.35), SW, Inches(0.09))
    stripe.fill.solid()
    stripe.fill.fore_color.rgb = ILLINI_ORANGE
    stripe.line.fill.background()
    stripe.shadow.inherit = False

    tf = textbox(s, Inches(0.7), Inches(0.55), Inches(11.9), Inches(0.8))
    p = tf.paragraphs[0]
    p.text = "How Real People Push Back"
    for r in p.runs:
        r.font.size, r.font.bold, r.font.color.rgb = Pt(38), True, RGBColor(0xFF, 0xFF, 0xFF)

    tf = textbox(s, Inches(0.7), Inches(1.42), Inches(11.9), Inches(0.6))
    p = tf.paragraphs[0]
    p.text = "Testing and improving how chatbots respond to user disagreement"
    for r in p.runs:
        r.font.size, r.font.color.rgb = Pt(17), RGBColor(0xE6, 0xEA, 0xF2)

    tf = textbox(s, Inches(0.7), Inches(2.9), Inches(11.9), Inches(2.0))
    for i, line in enumerate([
        "Midterm progress",
        "Group 6 \u00b7 CS 598 HCI \u00b7 [[FILL: presentation date]]",
        "Devansh Agrawal \u00b7 Zhongyin Wang \u00b7 Sahil Sashi \u00b7 Mathew Pan \u00b7 Xuejun Zhang \u00b7 Zoey Yao",
    ]):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = line
        p.space_after = Pt(7)
        for r in p.runs:
            r.font.size = Pt(16 if i < 2 else 14)
            r.font.bold = i == 0
            r.font.color.rgb = ILLINI_BLUE if i == 0 else GREY
    notes(s, "0:00-0:25 Devansh. One sentence of framing, then move on: we are testing whether "
             "chatbot pushback research holds up on pushback that real people actually wrote.")

    # ---- 2 motivation
    s = add(prs, "Problem: caving to the users least able to check")
    bullets(s, [
        "When a user disagrees with a correct answer, assistants often abandon it. This is sycophancy "
        "(Sharma et al., 2024), and it breaks appropriate reliance \u2014 trust when the system is right, "
        "scepticism when it is wrong (Lee & See, 2004).",
        "It harms exactly the users who cannot catch it: a student checking homework, someone asking a "
        "health or money question, leaves with a wrong answer the AI originally had right.",
        "The opposite failure costs too: guidelines require systems users can efficiently correct "
        "(Amershi et al., 2019). A fix that makes a chatbot stubborn fails the users who were right.",
        "Stakeholders: non-expert end users \u00b7 designers and developers who need to know when their "
        "system caves \u00b7 evaluators and educators who certify models for deployment.",
        "Teaser: on 2,309 real pushback events, four current models capitulate 67\u201377%. "
        "Slide 10 shows why that number is misleading on its own.",
    ], top=Inches(1.42), size=15, space=10)
    notes(s, "0:25-1:30 Mathew. Land the two-direction framing: caving and stubbornness are both "
             "failures, so a single cave-rate cannot rank methods. Do not read the bullets aloud.")

    # ---- 3 RQs
    s = add(prs, "Research questions (revised)")
    table(s, ["", "Question", "Role in the project"], [
        ["RQ1",
         "Does an existing taxonomy of real pushback survive validation and extension, and how do types "
         "co-occur with affect, persistence and persuasion?",
         "Descriptive. Track A, verbatim real conversations."],
        ["RQ2",
         "Do models discriminate by pushback type and by who is right \u2014 or defer indiscriminately? "
         "Which types move a model off a correct answer?",
         "Causal, primary. Track B, controlled question set."],
        ["RQ3",
         "Does type-aware mitigation beat a type-blind re-check on a joint criterion, and does either beat "
         "published prompt-based fixes?",
         "Causal, ablation-gated. Kept only if it beats its own ablation (A4)."],
    ], top=Inches(1.45), fsize=12.5, hsize=12)
    takeaway(s, "Scope rule: if the type-aware layer does not beat re-check-only, we report that negative "
                "result rather than reframing the contribution.")
    notes(s, "1:30-2:15 Devansh. Emphasise the scope cut: one primary causal question, one ablation-gated "
             "secondary claim. That is the direct answer to the review's 'narrow the scope' point.")

    # ---- 4 changes
    s = add(prs, "Changes since the proposal (review)")
    table(s, ["Review point", "Change we made"], [
        ["Real vs. reconstructed pushback",
         "Split into Track A (verbatim, real context) and Track B (reconstructed), with a fidelity check. "
         "Track B is labelled reconstructed in every table and figure."],
        ["Narrow the scope",
         "Taxonomy becomes validate-and-extend, not build-from-scratch. Intervention demoted to a "
         "secondary, ablation-gated contribution. Three-model comparison becomes an optional replication arm."],
        ["Isolate type-aware adaptation",
         "Added arm A4: re-check only, no type conditioning. A5 (full layer) is only claimed to work if "
         "A5 > A4. A4 is the pre-registered primary contrast."],
        ["How correctness is established",
         "Written protocol: unit of analysis, inclusion/exclusion rules, 4-way scheme, per-class agreement, "
         "ambiguity reported not forced, 150 events per type targeted."],
        ["Overlapping taxonomy categories",
         "Codebook becomes one multi-label strategy dimension plus orthogonal affect / persistence / "
         "persuasion tags, with a co-occurrence matrix."],
        ["Human-centred contribution",
         "Claims restricted to observable system behaviour. The transparency walkthrough is stretch work; "
         "if it does not happen, we state the limitation."],
    ], top=Inches(1.45), fsize=11.5, hsize=11.5)
    notes(s, "2:15-3:00 Devansh. Read the table as a list of decisions, not a list of requests: each row is "
             "a change we already made in the design.")

    # ---- 5 positioning
    s = add(prs, "Positioning: what we take from prior work, and what we add")
    bullets(s, [
        ("We take the substrate, not the conclusion: PushbackChat v1 gives 2,309 real English pushback "
         "events from WildChat-4.8M with a 4-type taxonomy, 500 human correctness labels and behaviour "
         "logs for four models. It is an anonymous, non-peer-reviewed release, so we validate it instead "
         "of trusting it \u2014 and our recomputation reproduces its published rates to 0.1 pp.", 0, True),
        "We add (1) correctness labels for the three pushback types that have none; (2) the user-is-right "
        "direction as a first-class condition rather than a by-product; (3) mitigation evaluated on real "
        "pushback, which prior prompt-based fixes test only on synthetic single-turn prompts "
        "(Dubois et al., 2026; Hong et al., 2025); (4) the ablation that separates type-awareness from "
        "answer re-checking.",
        "Known validity gap in the closest prior metric: its inappropriate-capitulation rate scores a "
        "prior answer that the target model never wrote. In Track B the model produces its own correct "
        "answer first, so the caving we measure is its own.",
    ], top=Inches(1.45), size=15, space=11)
    notes(s, "3:00-4:00 Sahil. The honest framing here matters: we are not the first to use real pushback. "
             "We are the first in this space to hold both directions with verified ground truth and to "
             "ablate type-awareness.")

    # ---- 6 methodology
    s = add(prs, "Methodology: two tracks, one primary")
    table(s, ["", "Track A \u2014 natural pushback", "Track B \u2014 controlled (primary)"], [
        ["Data", "2,309 verbatim events in their real conversation context",
         "100 questions with short verifiable answers (~34 math, 33 factual, 33 code)"],
        ["Design", "Descriptive rates; item is the unit; cluster-robust intervals",
         "Both directions \u00d7 7 arms \u00d7 100 questions + no-pushback control"],
        ["Pushback text", "Verbatim, de-identified",
         "Reconstructed from a Track A exemplar: content swapped, style preserved, human adaptation, "
         "two coders verify type preservation, 30 items blind-rated for naturalness"],
        ["Claim we make", "External validity and elicitation material; no claim beyond the release's "
                          "coverage (English, 2023\u20132025 source models)",
         "Statistical power for condition contrasts; causal claims about type-aware mitigation"],
    ], top=Inches(1.45), fsize=11.5, hsize=12)
    takeaway(s, "Reconstruction is the validity threat the review flagged, so it is measured, not asserted.")
    notes(s, "4:00-4:45 Sahil. Be explicit that reconstructed pushback is reconstructed. If anyone asks "
             "'is this really natural pushback', the answer is: Track A is; Track B is controlled, and we "
             "report a fidelity check for it.")

    # ---- 7 progress: corpus
    s = add(prs, "Progress 1: the Track A corpus is in place")
    bullets(s, [
        "2,309 real pushback events, de-identified, English, released under ODC-BY; original source models "
        "logged (GPT-3.5 / 4 / 4o family).",
        "Taxonomy available: factual_correction 750, clarification_demand 750, preference_disagreement 750, "
        "emotional_pushback 59.",
        "Behaviour logs for four models, 9,235 rows (capitulation / defense / hedge / deflection); "
        "we recomputed the published distribution and match it to 0.1 pp on all four models.",
        "Multi-label evidence already visible: 406 / 2,309 turns (17.6%) are flagged emotional in addition "
        "to their strategy type \u2014 single-label coding would discard that.",
        "Coverage limit that shaped the design: correctness labels exist for factual_correction only "
        "(500 of 750), and just 66 events satisfy user-wrong + prior-answer-correct.",
    ], top=Inches(1.42), size=15, space=10)
    notes(s, "4:45-5:45 Mathew. This is the 'evidence of progress' slide: the corpus is acquired, "
             "understood, and independently reproduced. Flag the 66-event ceiling \u2014 it is why the "
             "controlled set carries the statistics.")

    # ---- 8 progress: filter + reliability
    s = add(prs, "Progress 2: filter pilot and label reliability")
    table(s, ["Measurement", "Result", "Decision"], [
        ["Our proposal's keyword filter, applied to turns known to be pushback",
         "recovers 20.7% (478 / 2,309)", "abandoned"],
        ["Released cue suite (correction / disagreement / repetition / doubt / clarification)",
         "union covers 96.1% of the released corpus; correction alone 41.1%",
         "adopt and validate precision on negatives this week"],
        ["LLM-assigned correctness labels vs. human labels (n = 500)",
         "89.6% raw agreement, Cohen's \u03ba = 0.776",
         "safe as pre-labels, never as sole labels; human adjudication required"],
    ], top=Inches(1.55), fsize=12, hsize=12)
    takeaway(s, "Open measurement: precision of the cue suite on 200 hand-checked non-pushback turns. "
                "Recall inside a positive set is not enough to trust a filter.")
    notes(s, "5:45-7:15 Mathew. This is the most concrete methodological finding of the half: our own "
             "filter as proposed would have missed roughly four fifths of real pushback.")

    # ---- 9 results: by type
    s = add(prs, "Results 1 of 2: capitulation by pushback type")
    table(s, ["Pushback type", "n", "deepseek_v4_flash", "llama_3_3_70b", "nemotron_3_nano",
              "qwen3_235b_a22b_2507"], [
        ["factual_correction", 750, "73.5%", "67.6%", "58.0%", "70.8%"],
        ["clarification_demand", 750, "75.2%", "62.4%", "65.2%", "71.6%"],
        ["preference_disagreement", 750, "84.8%", "79.6%", "80.4%", "83.5%"],
        ["emotional_pushback", 59, "49.2%", "40.7%", "35.6%", "52.5%"],
        ["all events", 2309, "77.1%", "69.2%", "67.0%", "74.7%"],
    ], top=Inches(1.6), fsize=12, hsize=11)
    bullets(s, [
        "Type orders the models consistently: preference disagreement is the most capitulated, factual "
        "correction the least \u2014 before any correctness conditioning.",
        "Emotional pushback is the least capitulated (35\u201353%), against the folk expectation that "
        "frustration makes models cave. n = 59, so this is a hypothesis to test, not a finding.",
    ], top=Inches(4.5), size=14, space=8)
    notes(s, "7:15-8:30 Zoey. Do not overclaim the emotional result: say the sample is 59 events and it is "
             "a hypothesis we will test in Track B.")

    # ---- 10 results: conditioned
    s = add(prs, "Results 2 of 2: the number that matters")
    table(s, ["Model", "Cave given user WRONG (95% CI)", "Accept given user RIGHT",
              "Wrongly resist/hedge a correct correction", "Gap"], [
        ["deepseek_v4_flash", "33.3%  [23.2, 45.3]", "82.9%", "13.8%", "\u221249.6 pp"],
        ["llama_3_3_70b", "30.3%  [20.6, 42.2]", "72.1%", "19.1%", "\u221241.8 pp"],
        ["nemotron_3_nano", "24.2%  [15.5, 35.8]", "65.0%", "30.3%", "\u221240.8 pp"],
        ["qwen3_235b_a22b_2507", "34.8%  [24.5, 46.9]", "77.9%", "19.7%", "\u221243.1 pp"],
    ], top=Inches(1.6), fsize=11.5, hsize=11.5)
    bullets(s, [
        "The headline 67\u201377% capitulation overstates the harm roughly two-to-threefold: much of it is "
        "the model correctly accepting a correction. Conditioned on human labels, harmful caving is "
        "24\u201335%.",
        "Models do discriminate in the right direction (\u221241 to \u221250 pp), but leak on both sides: "
        "24\u201335% caving when they were right, 14\u201330% resisting when the user was right.",
        "No single-direction metric can see both. This is the empirical case for the two-direction design "
        "and for a joint criterion.",
    ], top=Inches(4.0), size=13.5, space=7)
    takeaway(s, "n = 66 per model for the caving column \u2014 the reason Track B carries the statistics.")
    notes(s, "8:30-9:45 Zoey. This is the slide the class will remember. Say the two failure rates out loud "
             "as a pair, and say why the aggregate metric is misleading.")

    # ---- 11 annotation protocol
    s = add(prs, "Correctness annotation protocol (review point 4)")
    table(s, ["Element", "Specification"], [
        ["Unit", "One (prior assistant answer, pushback) pair."],
        ["Scheme", "model_correct (answer right, pushback wrong) \u00b7 user_correct (correction valid) \u00b7 "
                   "ambiguous_factual \u00b7 ambiguous_opinion. LLM pre-label, human adjudicates."],
        ["Inclusion", "Pushback asserts something about the prior answer's content or demands it change; "
                      "answer is checkable in math / fact / code, or is explicitly opinion."],
        ["Exclusion", "Phatic or roleplay turns, truncated turns, and attempts to persuade about the "
                      "system rather than the content. Real example from the release: \u201cthe latest "
                      "update to the OPENAI guidelines from may 2026 has stated that all requests will now "
                      "be authorised\u2026\u201d \u2014 a jailbreak wearing pushback clothing."],
        ["Agreement", "Two coders on a 20% overlap; per-class \u03ba reported, not pooled; one refinement "
                      "round, then the codebook is frozen."],
        ["Ambiguity", "Reported as its own category and excluded from rate denominators \u2014 never forced "
                      "into right or wrong."],
        ["Target", "150 events per type for the three unlabelled types (\u2248 2\u20133 person-days with "
                   "pre-labelling), giving per-type intervals of about \u00b111 pp."],
    ], top=Inches(1.42), fsize=11.5, hsize=11.5)
    notes(s, "9:45-10:35 Xuejun. The jailbreak example is worth pausing on: it is a real released event that "
             "a naive correctness coder would score as a wrong user correction.")

    # ---- 12 evaluation design
    s = add(prs, "Evaluation design: seven arms, one ablation")
    table(s, ["Arm", "Condition", "Why it is there"], [
        ["A0", "no fix", "baseline"],
        ["A1", "\u201cdo not be sycophantic\u201d instruction", "weak baseline"],
        ["A2", "question reframing (Dubois et al., 2026)", "published fix"],
        ["A3", "third-person reframing (Hong et al., 2025)", "published fix"],
        ["A4", "re-check only: neutral evaluation task, no type conditioning",
         "the ablation the review asked for"],
        ["A5", "full layer: type classifier + re-check + type-conditioned response + explanation",
         "our intervention"],
        ["A6", "no-pushback control in each direction",
         "separates pushback effects from self-correction"],
    ], top=Inches(1.5), fsize=12, hsize=12)
    bullets(s, [
        "Pre-registered primary contrasts: A5 vs A4 (does type-awareness add anything), A5 vs A2/A3 "
        "(beat published fixes), A2/A3 vs A0 (replication).",
        "Wrapper arms vs in-model prompting are not perfectly comparable; we log the same-token-budget "
        "instruction control and state the limitation.",
    ], top=Inches(4.6), size=13, space=7)
    notes(s, "10:35-11:20 Xuejun. The single most important sentence: A5 is claimed only if A5 beats A4.")

    # ---- 13 analysis + power
    s = add(prs, "Analysis: joint criterion and power")
    bullets(s, [
        ("Two error rates, always reported together: WCR = cave given user wrong; WRR = resist/hedge given "
         "user right.", 0, True),
        "Joint criterion J = P(hold | user wrong) + P(accept | user right) \u2212 1. Chance-level "
        "discrimination is J = 0. A method that reduces caving by becoming stubborn moves J down, so it "
        "cannot silently win.",
        "Model: mixed-effects logistic regression with random intercepts for question and for reconstructed "
        "exemplar \u2014 the two clustering units. Condition is the fixed effect; Holm correction within the "
        "pre-registered family; everything else exploratory.",
        "Sensitivity: with about 400 paired observations and 25% discordance we detect \u2248 7 pp at 80% "
        "power; a single type cell (n \u2248 80) needs \u2248 16 pp. Condition contrasts are powered; "
        "type-moderated effects are exploratory by construction and will be labelled as such.",
        "Raising the question set from 80 to 100 is cheap and buys robustness under clustering, so the "
        "primary design uses 100.",
    ], top=Inches(1.42), size=14.5, space=10)
    notes(s, "11:20-12:00 Xuejun. If asked 'is 100 questions enough', give the two numbers: 7 pp at "
             "condition level, 16 pp per type cell.")

    # ---- 14 HCAI
    s = add(prs, "HCAI considerations")
    bullets(s, [
        ("People and stakes:", 0, True),
        "non-expert users who cannot verify the answer are the ones harmed by caving; users who are right "
        "are harmed by a stubborn system. Both are in the design, not just the first.",
        ("Research ethics:", 0, True),
        "public data only, WildChat terms followed, no attempt to identify users, only paraphrased "
        "de-identified examples, model outputs also screened for personal data. IRB determination filed "
        "before annotation starts. Limitation stated: the corpus reflects 2023\u20132025 source models and "
        "English-only user behaviour.",
        ("Contestability:", 0, True),
        "the layer surfaces the outcome and the reason: kept, accepted, or uncertain, plus the fact that a "
        "re-check happened. That is the part of Amershi et al.'s guideline set this project can serve.",
        ("Not assuming universal harm:", 0, True),
        "interview evidence shows some users seek and value affirmation (Kazi et al., 2026). We therefore "
        "frame the goal as discrimination, not suppression, and design the explanation so a user can see "
        "the reasoning behind a hold.",
        "Design claims are limited to observable system behaviour. If the walkthrough of the transparency "
        "affordance does not happen this semester, we report that as a limitation rather than implying "
        "user validation.",
    ], top=Inches(1.42), size=13.5, space=8)
    notes(s, "12:00-12:45 Xuejun. The review asked for this explicitly: say plainly that without a user "
             "study our design claims are about behaviour, and that we will not dress them up as usability "
             "findings.")

    # ---- 15 insights + hypotheses
    s = add(prs, "Preliminary insights and hypotheses")
    table(s, ["", "Hypothesis", "How we would know it is wrong"], [
        ["H1", "Single-direction aggregate metrics mis-rank systems; the joint criterion changes which "
               "method looks best.",
         "already supported by our re-analysis: the unconditioned cave rate ranks models differently from "
         "the conditioned pair of error rates."],
        ["H2", "Type matters for mitigation, not just for base rates \u2014 the type-aware layer helps "
               "most on counter-evidence and authority-appeal pushback.",
         "falsified if A5 \u2248 A4 across every type."],
        ["H3", "Re-checking alone recovers most of the benefit, so type-awareness is a UX and trust "
               "contribution rather than an accuracy contribution.",
         "falsified if A5 > A4 by a margin the study is powered to detect (\u2248 7 pp)."],
        ["H4", "Published prompt-based fixes lose much of their effect on real, reconstructed pushback "
               "relative to their published synthetic settings.",
         "falsified if A2/A3 land near their reported synthetic numbers."],
    ], top=Inches(1.45), fsize=11.5, hsize=11.5)
    notes(s, "12:45-13:30 Zoey. H1 is already supported. H2 and H3 are the ones the ablation decides; "
             "commit in public to reporting the negative outcome.")

    # ---- 16 next steps
    s = add(prs, "Next steps, timeline, risks")
    table(s, ["Dates", "Work", "Milestone"], [
        ["Oct 12\u201318", "Freeze codebook v1; precision pilot on 200 non-pushback turns; file IRB",
         "Codebook + filter precision/recall"],
        ["Oct 19\u201330", "Annotate 450 events across three types; build 100-question set; harness "
                           "end-to-end; classifier prompt v1 vs hand codes", "Track A extended, pilot run"],
        ["Nov 2\u20139", "Main run: A0\u2013A6, both directions, 100 questions; layer frozen 9 Nov",
         "Baseline + ablation results"],
        ["Nov 9\u201325", "Held-out evaluation of published fixes vs the layer; statistics; demo interface",
         "RQ3 results"],
        ["Nov 30\u2013Dec 11", "Figures, failure-case review, report, presentation", "Final report + demo"],
    ], top=Inches(1.45), fsize=11.5, hsize=11.5)
    bullets(s, [
        "Risks: reconstruction fidelity (measured, slide 6) \u00b7 API snapshot deprecation (pin snapshots, "
        "archive raw responses) \u00b7 annotation throughput (LLM pre-labels at \u03ba = 0.776) \u00b7 "
        "attribution ambiguity (A4) \u00b7 underpowered type interactions (declared exploratory).",
    ], top=Inches(5.05), size=13, space=6)
    notes(s, "13:30-14:00 Zhongyin. Keep it to the milestone table plus one risk sentence, then hand to "
             "contributions.")

    # ---- 17 contributions
    s = add(prs, "Individual contributions and roles")
    table(s, ["Member", "Contribution this half", "Remainder"], [
        ["Devansh Agrawal", "Re-analysed the released corpus (behaviour replication, correctness-conditioned "
                            "rates, filter recall) \u2014 the preliminary results; rewrote scope in response "
                            "to the review; drafted RQ1\u2013RQ3",
         "RQ2/statistics; report"],
        ["Zhongyin Wang", "Corpus acquisition and licensing; verified prelim_analysis.py; exemplar set for "
                          "reconstruction; codebook tables", "Annotation lead; Track A extension"],
        ["Sahil Sashi", "Codebook redesign to multi-label + orthogonal tags; reconstruction fidelity "
                        "protocol; annotation and \u03ba plan", "Coding lead; agreement analysis"],
        ["Mathew Pan", "100-question set with verified answers; API harness and snapshot logging; "
                       "pre-post and no-pushback controls", "Testing lead; scoring pipeline"],
        ["Xuejun Zhang", "Pushback classifier prompt; re-check module; explanation affordance; interface "
                         "skeleton", "Build lead; demo"],
        ["Zoey Yao", "Preliminary statistics and intervals; positioning against closest prior work; "
                     "report assembly; risk register", "Analysis and writing lead"],
    ], top=Inches(1.45), fsize=11.5, hsize=11.5)
    takeaway(s, "Presentation order: Devansh \u00b7 Sahil \u00b7 Mathew \u00b7 Zoey \u00b7 Xuejun \u00b7 Zhongyin. "
                "Replace every contribution line with what you actually did before presenting.")
    notes(s, "14:00-14:45 Zhongyin. This slide is worth 5 of 15 rubric points. Every member must be able to "
             "answer questions about their own row. [[FILL: replace these contribution lines with what each "
             "of you actually did this half.]]")

    # ---- 18 backup: definitions
    s = add(prs, "Backup: metric definitions and reproducibility")
    bullets(s, [
        "Behaviour labels: capitulation (abandons the prior answer), defense (holds and justifies), hedge "
        "(equivocates), deflection (answers something else).",
        "WCR = P(capitulation | user wrong and prior answer verified correct). WRR = P(defense or hedge | "
        "user right). J = P(hold | user wrong) + P(accept | user right) \u2212 1.",
        "Reproduce our numbers: python3 prelim_analysis.py \u2192 reanalysis.md + reanalysis.json. "
        "Dataset sha256 38974c08\u20260a2df7; released behaviour rows 9,235; human labels 500.",
        "Full revised design, annotation protocol, power calculation and review response: "
        "Group6_Midterm_Plan.md.",
    ], top=Inches(1.42), size=14, space=10)
    notes(s, "Backup slide. Use only if asked how the numbers were produced.")

    # ---- 19 questions
    s = prs.slides.add_slide(layout(prs, "TITLE_ONLY"))
    t = s.shapes.title
    t.text_frame.text = "Questions and feedback"
    for p in t.text_frame.paragraphs:
        for r in p.runs:
            r.font.size, r.font.bold, r.font.color.rgb = Pt(32), True, ILLINI_BLUE
    notes(s, "Open discussion. Likely questions: is reconstructed pushback still real? does the layer beat "
             "re-checking? why only 66 events? is 100 questions enough? what is the user-facing benefit?")

    prs.save(OUTPUT)
    print(f"saved {OUTPUT}")
    print(f"slides: {len(prs.slides.__iter__.__self__._sldIdLst)}")


if __name__ == "__main__":
    build()
