#!/usr/bin/env python3
"""Generate practice questions for the served curriculum indicators (P1-5).

The question bank was empty: `data/questions/` held one hand-written file and
nothing read it, so the app's quiz and paper flows rendered an empty selection.

This script writes **generated** practice items — one file per subject-grade,
`data/questions/<subject>/<grade>.generated.json` — from a small set of *rules*.
Every rule is arithmetic the script itself computes, so an answer is correct by
construction and a reviewer checks the rule, not 500 items:

    place-value     "What is the value of the digit 7 in 4,752?"        -> 700
    rounding        "Round 47,382 to the nearest hundred."              -> 47,400
    factors         "Which of these is a factor of 36?"                  -> the divisor
    hcf / lcm       the two numbers are stated, the answer computed
    …

Two rules matter more than the amount:

  * **Generated is labelled.** Each item carries `source: "generated:<rule>"`,
    and the build script keeps authored items in their own file, so nothing
    hand-written is ever overwritten and a teacher can see which is which.
  * **A rule only fires on a matching indicator.** The trigger is the served
    indicator text; an indicator no rule matches gets no questions, and the run
    prints that coverage number rather than padding it.

    python3 scripts/generate_question_bank.py                    # report
    python3 scripts/generate_question_bank.py --apply            # write files
    python3 scripts/generate_question_bank.py --subject mathematics --apply
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CURRICULUM = ROOT / "data" / "curriculum"
OUT = ROOT / "data" / "questions"

# Only mathematics: every rule below answers with arithmetic this script can
# check, which is what makes a generated bank defensible. A language or science
# rule would need a human author, so those subjects stay authored-only.
GENERATED_SUBJECTS = ("mathematics",)

# Primary only. The rules are arithmetic, and they match the primary syllabus'
# wording ("add whole numbers", "find the perimeter …"). At B7-B9 the same words
# appear in algebra and geometry indicators where an arithmetic item would be
# wrong for the indicator it hangs off, so the JHS grades stay authored-only
# until there are rules written for them.
GENERATED_GRADES = ("B2", "B3", "B4", "B5", "B6")

ITEMS_PER_INDICATOR = 3


def indicator_text(record: dict) -> str:
    return " ".join(str(record.get(k) or "") for k in ("ind_desc", "cs_desc")).lower()


def up_to(text: str, default: int) -> int:
    """The number range the indicator itself states, e.g. "up to 100,000".

    Following the indicator matters: an item about a six-digit number in an
    indicator that tops out at 10,000 is off the lesson the teacher is teaching.
    """
    match = re.search(r"up to (?:and from )?([\d][\d,]*)", text)
    if not match:
        return default
    value = int(match.group(1).replace(",", ""))
    return value if value >= 20 else default


# Default ceilings per grade, used when the indicator states no range.
GRADE_CEILING = {"B2": 1000, "B3": 10000, "B4": 10000, "B5": 100000, "B6": 1000000}


def num(n: int) -> str:
    """Thousands separators, the way the Ghanaian syllabus writes numerals."""
    return f"{n:,}"


def mcq(prompt, answer, distractors, marks=1, difficulty="core"):
    """An MCQ whose options are shuffled deterministically by the caller's RNG."""
    return {"type": "mcq", "prompt": prompt, "answer": str(answer),
            "distractors": [str(d) for d in distractors], "marks": marks,
            "difficulty": difficulty}


def short(prompt, answer, marks=2, difficulty="core"):
    return {"type": "short", "prompt": prompt, "answer": str(answer),
            "options": None, "marks": marks, "difficulty": difficulty}


# ─────────────────────────────────────────────────────────────── the rules ────
# Each rule: (id, regex over the indicator text, builder(rng) -> [question, …]).
# A builder states its own numbers in the prompt and computes the answer.

def r_place_value(rng, ctx):
    # One digit below the ceiling ("up to 10,000" gives four-digit numbers) and
    # never fewer than four: a three-digit number has almost nothing to ask about.
    ceiling = max(10000, ctx["ceiling"])
    digits = max(4, len(str(ceiling)) - 1)
    number = rng.randint(10 ** (digits - 1), 10 ** digits - 1)
    text = str(number)
    # The units place makes a question with an obvious answer ("the 6 in 756"),
    # so the digit asked about is never the last one.
    position = rng.randint(2, digits)
    digit = int(text[-position])
    if digit == 0:
        return []
    value = digit * 10 ** (position - 1)
    return [
        mcq(f"What is the value of the digit {digit} in {num(number)}?",
            num(value),
            [num(digit * 10 ** (position - 2)), num(value * 10), num(digit)],
            difficulty="core"),
        short(f"Write {num(number)} in expanded form.",
              " + ".join(f"{int(d)} x {10 ** (len(text) - 1 - i)}"
                         for i, d in enumerate(text) if d != "0"),
              marks=2),
    ]


def r_read_write(rng, ctx):
    ceiling = max(2000, ctx["ceiling"])
    number = rng.randint(1000, ceiling - 1)
    words = number_to_words(number)
    return [
        short(f"Write {num(number)} in words.", words, marks=2),
        short(f"Write '{words}' in figures.", num(number), marks=2),
    ]


def r_compare(rng, ctx):
    ceiling = max(1000, ctx["ceiling"])
    a, b = rng.randint(100, ceiling), rng.randint(100, ceiling)
    if a == b:
        b += 1
    symbol = ">" if a > b else "<"
    bigger, smaller = max(a, b), min(a, b)
    return [
        mcq(f"Which symbol makes this true?  {num(a)}  ___  {num(b)}", symbol, ["<", ">", "="],
            difficulty="core"),
        short(f"Arrange in order from smallest to largest: {num(bigger)}, {num(smaller)}.",
              f"{num(smaller)}, {num(bigger)}", marks=2),
    ]


def r_round(rng, ctx):
    number = rng.randint(1000, max(2000, ctx["ceiling"]) - 1)
    place, label = rng.choice([(10, "ten"), (100, "hundred"), (1000, "thousand"), (10000, "ten thousand")])
    rounded = int(round(number / place)) * place
    wrong = [rounded + place, rounded - place, (number // place) * place]
    return [
        mcq(f"Round {num(number)} to the nearest {label}.", num(rounded),
            [num(w) for w in wrong if w != rounded][:3], difficulty="core"),
    ]


def r_factors(rng, ctx):
    n = rng.choice([12, 16, 18, 20, 24, 28, 30, 36, 40, 45, 48, 60])
    factors = [d for d in range(1, n + 1) if n % d == 0]
    answer = rng.choice([d for d in factors if 1 < d < n])
    distractors = [d for d in (2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 14, 15, 16, 18, 20, 24) if n % d and d != answer]
    return [
        mcq(f"Which of these numbers is a factor of {n}?", answer, rng.sample(distractors, 3)),
        short(f"Write all the factors of {n}.", ", ".join(str(f) for f in factors), marks=2),
    ]


def r_prime(rng, ctx):
    limit = rng.choice([30, 50, 60, 100])
    primes = [n for n in range(2, limit + 1) if all(n % d for d in range(2, int(n ** 0.5) + 1))]
    p = rng.choice(primes)
    composites = [n for n in range(4, limit + 1) if n not in primes]
    c = rng.choice(composites)
    return [
        mcq(f"Which of these is a prime number?", p, rng.sample(composites, 3)),
        short(f"Write the first five prime numbers.", ", ".join(str(n) for n in primes[:5]), marks=2),
        mcq(f"Is {c} a prime number or a composite number?", "Composite", ["Prime", "Neither", "Both"]),
    ]


def r_odd_even(rng, ctx):
    n = rng.randint(10, 999)
    other = n + 1
    return [
        mcq(f"Is {n} an odd number or an even number?", "Even" if n % 2 == 0 else "Odd", ["Odd", "Even"]),
        short(f"Write the next even number after {num(other)}.", num(other + 1 + (other % 2)), marks=1),
    ]


def r_hcf(rng, ctx):
    limit = min(100, max(20, ctx["ceiling"]))
    a, b = rng.randint(12, limit), rng.randint(12, limit)
    hcf = _gcd(a, b)
    return [
        short(f"Find the highest common factor (HCF) of {a} and {b}.", hcf, marks=3),
    ]


def r_lcm(rng, ctx):
    limit = min(40, max(12, ctx["ceiling"]))
    a, b = rng.randint(4, limit), rng.randint(4, limit)
    lcm = a * b // _gcd(a, b)
    return [
        short(f"Find the lowest common multiple (LCM) of {a} and {b}.", lcm, marks=3),
    ]


def r_multiples(rng, ctx):
    n = rng.randint(3, 12)
    multiples = [n * i for i in range(1, 6)]
    return [
        short(f"Write the first five multiples of {n}.", ", ".join(str(m) for m in multiples), marks=2),
        mcq(f"Which of these is a multiple of {n}?", multiples[2],
            [multiples[2] + 1, multiples[2] - 1, multiples[2] + 2]),
    ]


def r_addition(rng, ctx):
    ceiling = max(100, ctx["ceiling"])
    a, b = rng.randint(100, ceiling), rng.randint(100, ceiling)
    return [short(f"Add: {num(a)} + {num(b)} = ", num(a + b), marks=2)]


def r_subtraction(rng, ctx):
    ceiling = max(1000, ctx["ceiling"])
    a = rng.randint(ceiling // 2, ceiling)
    b = rng.randint(100, a - 1)
    return [short(f"Subtract: {num(a)} - {num(b)} = ", num(a - b), marks=2)]


def r_multiplication(rng, ctx):
    ceiling = max(100, ctx["ceiling"])
    a, b = rng.randint(12, max(13, min(999, ceiling))), rng.randint(3, 99)
    return [short(f"Multiply: {num(a)} x {num(b)} = ", num(a * b), marks=2)]


def r_division(rng, ctx):
    ceiling = max(100, ctx["ceiling"])
    b = rng.randint(3, 25)
    quotient = rng.randint(4, max(5, min(120, ceiling // b)))
    return [short(f"Divide: {num(b * quotient)} ÷ {b} = ", quotient, marks=2)]


def r_fraction_of(rng, ctx):
    denom = rng.choice([2, 3, 4, 5, 6, 8, 10])
    numer = rng.randint(1, denom - 1)
    whole = denom * rng.randint(2, 12)
    answer = whole // denom * numer
    return [
        short(f"What is {numer}/{denom} of {whole}?", answer, marks=2),
    ]


def r_equivalent_fraction(rng, ctx):
    numer, denom = rng.randint(1, 5), rng.randint(numer := rng.randint(2, 9), 12)
    if denom <= numer:
        denom = numer + rng.randint(1, 5)
    factor = rng.randint(2, 5)
    return [
        mcq(f"Which fraction is equivalent to {numer}/{denom}?",
            f"{numer * factor}/{denom * factor}",
            [f"{numer + factor}/{denom + factor}", f"{numer * factor}/{denom + factor}",
             f"{numer + 1}/{denom + 1}"]),
    ]


def r_decimal_place(rng, ctx):
    value = round(rng.uniform(0.1, 99.9), rng.choice([1, 2]))
    return [
        short(f"Write {value} as a fraction in its simplest form.", _decimal_to_fraction(value), marks=2),
    ]


def r_measurement(rng, ctx):
    if ctx["grade"] in ("B2", "B3"):
        # Primary 2-3 measure in centimetres and metres; kilometres come later.
        metres = rng.randint(2, 40)
        cm = rng.randint(10, 90)
        return [
            short(f"Convert {metres} m {cm} cm to centimetres.", metres * 100 + cm, marks=2),
            short(f"Convert {metres * 100 + cm} cm to metres and centimetres.",
                  f"{metres} m {cm} cm", marks=2),
        ]
    km = rng.randint(2, 40)
    m = rng.randint(100, 900)
    return [
        short(f"Convert {km} km {m} m to metres.", km * 1000 + m, marks=2),
        short(f"Convert {km * 1000 + m} metres to kilometres and metres.",
              f"{km} km {m} m", marks=2),
    ]


def r_perimeter_area(rng, ctx):
    length, width = rng.randint(4, 30), rng.randint(3, 25)
    return [
        short(f"A rectangle is {length} cm long and {width} cm wide. Find its perimeter.",
              f"{2 * (length + width)} cm", marks=2),
        short(f"A rectangle is {length} cm long and {width} cm wide. Find its area.",
              f"{length * width} cm²", marks=2),
    ]


def r_time(rng, ctx):
    hours, minutes = rng.randint(1, 5), rng.choice([15, 20, 25, 30, 40, 45])
    start_hour = rng.randint(6, 9)
    end_minutes = start_hour * 60 + hours * 60 + minutes
    return [
        short(f"A lesson starts at {start_hour}:00 and lasts {hours} hour(s) {minutes} minutes. "
              f"What time does it end?", f"{end_minutes // 60}:{end_minutes % 60:02d}", marks=2),
    ]


def r_money(rng, ctx):
    price = rng.choice([1.5, 2.5, 3.5, 4.25, 5.5, 6.75])
    count = rng.randint(3, 12)
    total = round(price * count, 2)
    return [
        short(f"A pen costs GH¢{price:.2f}. How much do {count} pens cost?",
              f"GH¢{total:.2f}", marks=2),
    ]


def r_average(rng, ctx):
    values = [rng.randint(10, 90) for _ in range(5)]
    total = sum(values)
    return [
        short(f"Find the average of {', '.join(str(v) for v in values)}.",
              f"{total / 5:g}", marks=2),
    ]


def r_percentage(rng, ctx):
    percent = rng.choice([5, 10, 15, 20, 25, 50])
    of = rng.choice([20, 40, 60, 80, 120, 200])
    value = of * percent / 100
    return [
        short(f"What is {percent}% of {of}?", f"{value:g}", marks=2),
    ]


RULES = [
    ("place-value", r"\bplace value\b|positions? (?:around|in) a given number|values? of (?:the )?digits?", r_place_value),
    ("read-write-numbers", r"read and write numbers|in figures and in words", r_read_write),
    ("compare-order", r"compare and order|arrange .*order|order(?:ing)? whole numbers", r_compare),
    ("rounding", r"\bround(?:ing)?\b", r_round),
    ("factors", r"factors of whole numbers|identify the factors|factors? of any", r_factors),
    ("primes", r"prime numbers? and composite|prime numbers? between", r_prime),
    ("odd-even", r"even and odd numbers", r_odd_even),
    ("hcf", r"highest common factor", r_hcf),
    ("lcm", r"lowest common multiple|least common multiple", r_lcm),
    ("multiples", r"multiples of whole numbers|common multiples|multiples of \d", r_multiples),
    ("addition", r"add(?:ing)? (?:and subtract )?(?:up to )?(?:whole )?numbers|addition of", r_addition),
    ("subtraction", r"subtract(?:ing|ion)? (?:whole )?numbers", r_subtraction),
    ("multiplication", r"multipl(y|ication)|times table", r_multiplication),
    ("division", r"divid(e|ing|es)|division of", r_division),
    ("fraction-of", r"fraction of (?:a )?(?:whole |given )?(?:number|quantity)|find the fraction of", r_fraction_of),
    ("equivalent-fractions", r"equivalent fractions", r_equivalent_fraction),
    ("decimals", r"decimal (?:place value|numbers|fractions)|decimals?", r_decimal_place),
    ("measurement", r"convert .*(?:kilomet|metre|meter)|length|mass|capacity", r_measurement),
    ("perimeter-area", r"perimeter|area of (?:a )?(?:rectangle|square|triangle)", r_perimeter_area),
    ("time", r"\btime\b|clock|duration", r_time),
    ("money", r"money|cedi|GH¢|cost|price", r_money),
    ("average", r"average|mean of", r_average),
    ("percentage", r"percentage|per cent|percent", r_percentage),
]


def _gcd(a, b):
    while b:
        a, b = b, a % b
    return a


ONES = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
        "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen",
        "eighteen", "nineteen"]
TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]


def number_to_words(n: int) -> str:
    """Cardinal words, up to the millions the Basic 6 syllabus counts to."""
    if n < 0:
        return "minus " + number_to_words(-n)
    if n < 20:
        return ONES[n]
    if n < 100:
        return TENS[n // 10] + ("-" + ONES[n % 10] if n % 10 else "")
    if n < 1000:
        return ONES[n // 100] + " hundred" + (f" and {number_to_words(n % 100)}" if n % 100 else "")
    for scale, word in ((1_000_000_000, "billion"), (1_000_000, "million"), (1000, "thousand")):
        if n >= scale:
            head = number_to_words(n // scale) + " " + word
            rest = n % scale
            if not rest:
                return head
            # "… thousand and forty-four" reads the way the syllabus writes it;
            # above a hundred the "and" is dropped ("one million two hundred …").
            return head + (" and " if rest < 100 else " ") + number_to_words(rest)
    raise ValueError(n)


def _decimal_to_fraction(value: float) -> str:
    from fractions import Fraction
    f = Fraction(value).limit_denominator(1000)
    return f"{f.numerator}/{f.denominator}" if f.denominator != 1 else str(f.numerator)


def questions_for(code: str, record: dict, grade: str = "B4") -> list[dict]:
    """Every rule that matches the indicator's text, run deterministically."""
    text = indicator_text(record)
    ctx = {"ceiling": up_to(text, GRADE_CEILING.get(grade, 10000)), "grade": grade, "text": text}
    out = []
    for rule_id, pattern, builder in RULES:
        if not re.search(pattern, text):
            continue
        rng = random.Random(f"{code}|{rule_id}")
        for item in builder(rng, ctx)[:ITEMS_PER_INDICATOR]:
            if not item or not item.get("prompt"):
                continue
            options = None
            if item["type"] == "mcq":
                options = [item["answer"], *item.get("distractors", [])]
                options = list(dict.fromkeys(options))  # a distractor equal to the answer is dropped
                rng.shuffle(options)
                # Option letters, the way a printed paper lists them.
                item = {**item, "options": options,
                        "answerLetter": "ABCD"[options.index(item["answer"])]}
            out.append({
                "id": f"{code}-{rule_id}-{len(out) + 1}",
                "indicatorCode": code,
                "prompt": item["prompt"],
                "type": item["type"],
                "options": options,
                "answer": item["answer"],
                **({"answerLetter": item["answerLetter"]} if item.get("answerLetter") else {}),
                "marks": item.get("marks", 1),
                "difficulty": item.get("difficulty", "core"),
                "source": f"generated:{rule_id}",
            })
            if len(out) >= ITEMS_PER_INDICATOR:
                break
    return out


def db_paths(subjects) -> list[tuple[str, str, Path]]:
    found = []
    for subject in subjects:
        for path in sorted(CURRICULUM.glob(f"{subject}_*_curriculum_db*.json")):
            grade = re.search(r"_((?:B|KG)\d+)_", path.name).group(1)
            if grade in GENERATED_GRADES:
                found.append((subject, grade, path))
    return found


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--subject", action="append", default=None,
                    help=f"subject to generate for (default: {' '.join(GENERATED_SUBJECTS)})")
    ap.add_argument("--apply", action="store_true", help="write the generated files")
    args = ap.parse_args()

    subjects = args.subject or list(GENERATED_SUBJECTS)
    total_items = total_indicators = covered = 0

    for subject, grade, path in db_paths(subjects):
        rows = json.loads(path.read_text(encoding="utf-8"))
        items, hit = [], 0
        for code, record in rows.items():
            questions = questions_for(code, record, grade)
            if questions:
                hit += 1
            items.extend(questions)
        total_items += len(items)
        total_indicators += len(rows)
        covered += hit

        per_rule = {}
        for item in items:
            per_rule[item["source"]] = per_rule.get(item["source"], 0) + 1
        rules = " ".join(f"{k.split(':')[1]}={v}" for k, v in sorted(per_rule.items()))
        print(f"  {subject:12} {grade:4} {len(items):4} questions · "
              f"{hit:3}/{len(rows):3} indicators covered ({hit / max(1, len(rows)) * 100:4.0f}%)  {rules}")

        if args.apply and items:
            out_dir = OUT / subject
            out_dir.mkdir(parents=True, exist_ok=True)
            payload = {
                "subjectId": subject,
                "grade": grade,
                "generatedBy": "scripts/generate_question_bank.py",
                "items": items,
            }
            (out_dir / f"{grade}.generated.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print(f"\n{total_items} questions for {total_indicators} indicators "
          f"({covered} covered, {total_indicators - covered} left for an author)")
    if not args.apply:
        print("report only — pass --apply to write data/questions/<subject>/<grade>.generated.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
