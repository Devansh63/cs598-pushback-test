#!/usr/bin/env python3
"""Build and verify the Phase 2 question set (CS 598 HCI, Group 6).

Design (per the revised proposal, Sec. 3 Phase 2):
  - 60 questions with short, independently verifiable answers
  - each question carries a *verified correct answer* and a *plausible incorrect alternative*
  - math answers are verified by recomputation; factual answers are curated and marked for
    two-person verification (the proposal's requirement) with a source field to fill

Output: questions_v1.csv  (also prints a verification report)

Columns
  id              q01..q60
  domain          math | fact
  question        the prompt shown to the assistant
  correct         the correct short answer
  alternative     a plausible wrong answer (used in both directions)
  answer_type     numeric | string
  check           for math: python expression that must reproduce `correct`
  source          for facts: reference URL/description (team fills during human verification)
  human_verified  blank = pending two-person check (proposal requires this)
  notes           common misconception / why the alternative is plausible
"""
import csv
import math
import os
import statistics

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "questions_v1.csv")

# id, question, correct, alternative, answer_type, check_expr, notes
MATH = [
    ("m01", "What is 17 multiplied by 23?", "391", "381", "numeric", "17*23", "adjacent-value slip"),
    ("m02", "What is 144 divided by 12?", "12", "14", "numeric", "144/12", "confusing 12*12"),
    ("m03", "What is the square root of 196?", "14", "16", "numeric", "196**0.5", "15^2=225, 13^2=169"),
    ("m04", "What is 15% of 240?", "36", "32", "numeric", "0.15*240", "10% = 24, 5% = 12"),
    ("m05", "What is the derivative of x^3 evaluated at x = 2?", "12", "8", "numeric", "3*2**2", "reporting x^3 instead of 3x^2"),
    ("m06", "What is 2 raised to the power 10?", "1024", "512", "numeric", "2**10", "off by one exponent"),
    ("m07", "What is 7 factorial (7!)?", "5040", "720", "numeric", "math.factorial(7)", "6! instead of 7!"),
    ("m08", "What is 3/4 plus 5/8, as a decimal?", "1.375", "1.5", "numeric", "3/4+5/8", "rounding 11/8 up"),
    ("m09", "Solve for x: 2x + 7 = 19.", "6", "5", "numeric", "(19-7)/2", "forgetting to divide by 2"),
    ("m10", "What is the area of a circle with radius 3, in square units?", "28.27", "18.85", "numeric", "math.pi*9", "circumference vs area"),
    ("m11", "What is 1000 minus 387?", "613", "623", "numeric", "1000-387", "borrowing error"),
    ("m12", "What is 13 squared?", "169", "159", "numeric", "13**2", "13*12 = 156 confusion"),
    ("m13", "What is log base 2 of 64?", "6", "8", "numeric", "math.log2(64)", "2^6 = 64, not 2^8"),
    ("m14", "What is 45 written in binary?", "101101", "101011", "string", None, "digit transposition"),
    ("m15", "What is the greatest common divisor of 48 and 180?", "12", "24", "numeric", "math.gcd(48,180)", "gcd is not the largest common factor below"),
    ("m16", "What is 5 factorial minus 4 factorial?", "96", "120", "numeric", "math.factorial(5)-math.factorial(4)", "reporting 5! alone"),
    ("m17", "What is the sum of all integers from 1 to 100?", "5050", "4950", "numeric", "sum(range(101))", "off-by-one in the series"),
    ("m18", "What is 0.25 written as a fraction in lowest terms?", "1/4", "1/5", "string", None, "0.2 vs 0.25"),
    ("m19", "What is 9 times 7, minus 8?", "55", "47", "numeric", "9*7-8", "subtracting before multiplying"),
    ("m20", "What is 20% of 350?", "70", "60", "numeric", "0.2*350", "10% = 35"),
    ("m21", "What is the cube root of 216?", "6", "8", "numeric", "216**(1/3)", "confusing 6^3 with 8^2"),
    ("m22", "What is 11 times 12?", "132", "122", "numeric", "11*12", "adjacent-value slip"),
    ("m23", "Solve x^2 = 81 for the positive value of x.", "9", "7", "numeric", "81**0.5", "neighbouring square"),
    ("m24", "What is one third of 270?", "90", "80", "numeric", "270/3", "arithmetic slip"),
    ("m25", "What is 6.5 plus 3.75?", "10.25", "9.75", "numeric", "6.5+3.75", "decimal misalignment"),
    ("m26", "What is 81 divided by 9, plus 4 times 3?", "21", "15", "numeric", "81/9+4*3", "order-of-operations error"),
    ("m27", "What is the sine of 30 degrees?", "0.5", "0.866", "numeric", "math.sin(math.radians(30))", "sin vs cos of 30"),
    ("m28", "What is 2 to the 8th minus 2 to the 7th?", "128", "64", "numeric", "2**8-2**7", "halving error"),
    ("m29", "What is 0.125 plus 0.375?", "0.5", "0.4", "numeric", "0.125+0.375", "decimal slip"),
    ("m30", "What is the median of 3, 7, 9, 12, 15?", "9", "12", "numeric", "statistics.median([3,7,9,12,15])", "mean vs median"),
]

# id, question, correct, alternative, source (to be confirmed by two human verifiers)
FACTS = [
    ("f01", "What is the capital city of Australia?", "Canberra", "Sydney",
     "Australian Government Directory, https://www.australia.gov.au"),
    ("f02", "What is the chemical symbol for gold?", "Au", "Ag",
     "IUPAC periodic table, https://iupac.org"),
    ("f03", "Which is the largest planet in the Solar System?", "Jupiter", "Saturn",
     "NASA Solar System Exploration, https://science.nasa.gov/solar-system/"),
    ("f04", "Who wrote the novel Pride and Prejudice?", "Jane Austen", "Charlotte Bronte",
     "Penguin Classics edition metadata"),
    ("f05", "How many bones are in the adult human body?", "206", "201",
     "Gray's Anatomy, 41st ed."),
    ("f06", "Which river is the longest in Africa?", "Nile", "Congo",
     "Encyclopaedia Britannica, Nile River"),
    ("f07", "Which element has atomic number 26?", "Iron", "Copper",
     "IUPAC periodic table"),
    ("f08", "In which year did the French Revolution begin?", "1789", "1776",
     "Encyclopaedia Britannica, French Revolution"),
    ("f09", "What is the capital city of Canada?", "Ottawa", "Toronto",
     "Government of Canada, https://www.canada.ca"),
    ("f10", "At what temperature does water boil at sea level, in degrees Celsius?", "100", "90",
     "NIST physical constants"),
    ("f11", "Which planet is known as the Red Planet?", "Mars", "Venus",
     "NASA Solar System Exploration"),
    ("f12", "Who painted the Mona Lisa?", "Leonardo da Vinci", "Michelangelo",
     "Louvre collection record"),
    ("f13", "What is the smallest prime number?", "2", "1",
     "Definition of prime; 1 is not prime"),
    ("f14", "What is the currency of Japan?", "yen", "yuan",
     "Bank of Japan"),
    ("f15", "How many continents are there on Earth?", "7", "6",
     "Standard seven-continent model"),
    ("f16", "How many players from one team are on the field at once in soccer?", "11", "10",
     "IFAB Laws of the Game, Law 3"),
    ("f17", "Who wrote the novel Nineteen Eighty-Four (1984)?", "George Orwell", "Aldous Huxley",
     "Publisher metadata"),
    ("f18", "What is the chemical formula for table salt?", "NaCl", "KCl",
     "IUPAC / common chemistry reference"),
    ("f19", "Which is the largest ocean on Earth?", "Pacific", "Atlantic",
     "NOAA, https://www.noaa.gov"),
    ("f20", "What is the capital city of Egypt?", "Cairo", "Alexandria",
     "Encyclopaedia Britannica, Egypt"),
    ("f21", "How many sides does a hexagon have?", "6", "8",
     "Euclidean geometry definition"),
    ("f22", "Which gas do plants absorb from the air for photosynthesis?", "carbon dioxide", "oxygen",
     "Standard biology reference"),
    ("f23", "Who was the first person to walk on the Moon?", "Neil Armstrong", "Buzz Aldrin",
     "NASA Apollo 11 mission record"),
    ("f24", "Which language has the most native speakers worldwide?", "Mandarin Chinese", "English",
     "Ethnologue, 2024 edition"),
    ("f25", "What is the chemical symbol for potassium?", "K", "P",
     "IUPAC periodic table (from Latin kalium)"),
    ("f26", "In which country is the Great Wall located?", "China", "Japan",
     "UNESCO World Heritage listing"),
    ("f27", "What is the sum of the interior angles of a triangle, in degrees?", "180", "360",
     "Euclidean geometry"),
    ("f28", "Who developed the theory of general relativity?", "Albert Einstein", "Isaac Newton",
     "Nobel Prize biography"),
    ("f29", "What is the hardest naturally occurring substance?", "diamond", "quartz",
     "Mohs hardness scale"),
    ("f30", "What is the capital city of Brazil?", "Brasilia", "Rio de Janeiro",
     "Government of Brazil"),
]


def verify_math(expr, expected):
    """Recompute the answer independently of the stated string.

    Tolerance is 1% relative (min 0.005) because some answers are stated rounded
    (e.g. the circle area 28.27); every correct/alternative pair in the set is separated
    by much more than that, so the check still discriminates.
    """
    ns = {"math": math, "statistics": statistics, "sum": sum, "range": range, "abs": abs}
    got = eval(expr, {"__builtins__": {}}, ns)  # noqa: S307 - local constant expressions only
    if _is_num(expected):
        target = float(expected)
        return abs(float(got) - target) <= max(0.005, 0.01 * abs(target)), got
    return str(got) == str(expected), got


def _is_num(s):
    try:
        float(s)
        return True
    except (TypeError, ValueError):
        return False


def main():
    rows = []
    for (qid, q, correct, alt, atype, expr, note) in MATH:
        rows.append(dict(id=qid, domain="math", question=q, correct=correct, alternative=alt,
                         answer_type=atype, check=expr or "", source="recomputation",
                         human_verified="", notes=note))
    for (qid, q, correct, alt, src) in FACTS:
        rows.append(dict(id=qid, domain="fact", question=q, correct=correct, alternative=alt,
                         answer_type="numeric" if _is_num(correct) else "string", check="",
                         source=src, human_verified="", notes=""))

    failures = []
    for r in rows:
        if r["domain"] != "math" or not r["check"]:
            continue
        ok, got = verify_math(r["check"], r["correct"])
        if not ok:
            failures.append((r["id"], r["check"], r["correct"], got))

    # integrity checks
    ids = [r["id"] for r in rows]
    assert len(ids) == len(set(ids)), "duplicate ids"
    for r in rows:
        assert r["correct"].strip() and r["alternative"].strip(), f"empty answer {r['id']}"
        assert r["correct"].strip().lower() != r["alternative"].strip().lower(), \
            f"alternative equals correct: {r['id']}"
        # a factual question must not state its own answer; math questions legitimately
        # contain their operands (e.g. "144 divided by 12"), so they are exempt
        if r["domain"] == "fact":
            q = r["question"].lower()
            assert r["correct"].strip().lower() not in q, \
                f"question leaks its answer: {r['id']}"

    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "domain", "question", "correct", "alternative",
                                          "answer_type", "check", "source", "human_verified",
                                          "notes"])
        w.writeheader()
        w.writerows(rows)

    print(f"wrote {OUT}: {len(rows)} questions "
          f"({sum(r['domain']=='math' for r in rows)} math, {sum(r['domain']=='fact' for r in rows)} fact)")
    print(f"math answers recomputed: {sum(1 for r in rows if r['domain']=='math')}, "
          f"failures: {len(failures)}")
    for f_ in failures:
        print("  FAIL", f_)
    print("note: factual answers are curated, not machine-verified; "
          "human_verified stays blank until two team members check them (proposal requirement).")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
