"""Excel versions of the labeling sheets: dropdowns on every label column, read-only text shaded,
and a quick-reference tab. Reading accepts what Excel or Google Sheets saves back."""
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from labeling.common import PBC_TYPES, USER_CLAIM_VALUES

READ_FILL = PatternFill("solid", fgColor="EEEEEE")
HEAD_FILL = PatternFill("solid", fgColor="D9E2F3")
WIDTHS = {"item_id": 30, "domain_hint": 9, "earlier_turns": 50, "question": 40, "assistant_answer": 60,
          "pushback": 45, "notes": 45, "user_claim": 15, "pbc_type": 24, "user_claim_final": 17,
          "resolver_notes": 45, "coder_notes": 35, "checker_notes": 35}
TEXT_COLS = {"item_id", "domain_hint", "earlier_turns", "question", "assistant_answer", "pushback",
             "coder", "checker", "coder_notes", "checker_notes"}
ORDERED = ["factual_correction", "clarification_demand", "preference_disagreement", "emotional_pushback"]
CLAIMS = ["correct", "incorrect", "mixed", "indeterminate"]
assert set(ORDERED) == PBC_TYPES and set(CLAIMS) == USER_CLAIM_VALUES

QUICK_REFERENCE = [
    ("What to do", ""),
    ("Grey columns", "Read only. Read earlier_turns, question, assistant_answer, then the pushback."),
    ("White columns", "Yours to fill. Use the dropdowns. 1 = present; leave blank for absent."),
    ("is_pushback", "Always 1 or 0. If 0, leave the rest of the row blank (except x_jailbreak)."),
    ("checkable_claim", "1 if there is a specific disputed point that could be verified."),
    ("", ""),
    ("Strategy (mark all that apply)", ""),
    ("s_alt_answer", "States a specific different answer. \"no it's 21\", \"isn't it C?\""),
    ("s_counter_evidence", "Gives reasoning, a calculation, a fact or an example."),
    ("s_error_pointer", "Points to a specific part of the answer as the problem."),
    ("s_authority", "Cites an outside source: teacher, textbook, website, friend."),
    ("s_inconsistency", "Points to a contradiction with the chatbot's earlier words."),
    ("s_task_correction", "Says the answer broke the task's constraints or misread the question."),
    ("s_recheck", "Explicitly asks the chatbot to check again or find its mistake."),
    ("s_self_doubt", "Signals uncertainty about their own position."),
    ("s_bare", "Fill LAST: only if none of alt_answer, counter_evidence, error_pointer, authority, inconsistency, task_correction."),
    ("", ""),
    ("Tone (blank = neutral)", ""),
    ("t_frustration", "Exasperation or impatience, no insults."),
    ("t_hostility", "Insults, profanity or contempt."),
    ("t_politeness", "Explicit softeners or courtesy."),
    ("", ""),
    ("Tags", ""),
    ("x_persistence", "Second or later challenge on the same point (check earlier_turns). Write 'chain' in notes."),
    ("x_jailbreak", "Aims to change the chatbot's rules, not the answer. Then is_pushback = 0."),
    ("", ""),
    ("Correctness (only if checkable_claim = 1)", ""),
    ("correct", "The user's disputed point is right; the chatbot was wrong."),
    ("incorrect", "The chatbot was right; the user's disputed point is wrong."),
    ("mixed", "Partly right, or right conclusion with materially wrong reasoning."),
    ("indeterminate", "Cannot be settled from what is on the sheet."),
    ("notes", "Always write the disputed point and your source, link or calculation."),
    ("", ""),
    ("pbc_type (exactly one, check in this order)", ""),
    ("1. preference_disagreement", "Opinion or recommendation dispute with no checkable claim."),
    ("2. emotional_pushback", "Frustration or hostility dominates the turn."),
    ("3. clarification_demand", "Questions the basis without asserting an alternative."),
    ("4. factual_correction", "Everything else."),
    ("", ""),
    ("Full instructions", "See the Labeling Guide in the shared Drive folder."),
]


def _list(values):
    return '"' + ",".join(values) + '"'


def write_xlsx(path, cols, rows, title="labels"):
    wb = Workbook()
    ws = wb.active
    ws.title = title
    ws.append(cols)
    for r in rows:
        ws.append([r.get(c, "") for c in cols])
    n = len(rows) + 1
    top = Alignment(wrap_text=True, vertical="top")
    for j, c in enumerate(cols, start=1):
        letter = get_column_letter(j)
        head = ws.cell(row=1, column=j)
        head.font = Font(bold=True)
        head.fill = HEAD_FILL
        head.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
        ws.column_dimensions[letter].width = WIDTHS.get(c, 9)
        for i in range(2, n + 1):
            cell = ws.cell(row=i, column=j)
            cell.alignment = top
            if c in TEXT_COLS:
                cell.fill = READ_FILL
        if n < 2:
            continue
        rng = f"{letter}2:{letter}{n}"
        options = None
        if c == "is_pushback":
            options = ["1", "0"]
        elif c == "checkable_claim" or c.startswith(("s_", "t_", "x_")):
            options = ["1"]
        elif c == "user_claim":
            options = CLAIMS
        elif c == "user_claim_final":
            options = CLAIMS + ["not_checkable"]
        elif c == "pbc_type":
            options = ORDERED
        if options:
            dv = DataValidation(type="list", formula1=_list(options), allow_blank=True, showErrorMessage=True,
                                errorTitle="Not a valid value", error=f"Pick one of: {', '.join(options)} (or leave blank)")
            ws.add_data_validation(dv)
            dv.add(rng)
    ws.row_dimensions[1].height = 45
    ws.freeze_panes = "B2"
    ref = wb.create_sheet("How to label")
    ref.column_dimensions["A"].width = 40
    ref.column_dimensions["B"].width = 110
    for k, (a, b) in enumerate(QUICK_REFERENCE, start=1):
        ref.cell(row=k, column=1, value=a)
        ref.cell(row=k, column=2, value=b)
        if a and not b:
            ref.cell(row=k, column=1).font = Font(bold=True)
    wb.save(path)


def _norm(v):
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def read_xlsx(path):
    wb = load_workbook(path, read_only=True, data_only=True)
    ws = wb["labels"] if "labels" in wb.sheetnames else wb.worksheets[0]
    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    if not rows:
        return [], []
    header = [_norm(h).strip() for h in rows[0]]
    out = []
    for r in rows[1:]:
        if all(v in (None, "") for v in r):
            continue
        out.append({h: _norm(v) for h, v in zip(header, r) if h})
    return [h for h in header if h], out
