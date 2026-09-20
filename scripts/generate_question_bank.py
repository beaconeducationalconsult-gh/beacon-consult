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

The rules come in two bands. The primary rules (B2–B6) are arithmetic over
primary wording. The JHS rules (B7–B9) were written because the primary ones
must **not** fire there: at JHS the same words sit inside algebra and geometry
indicators ("multiplication of binomial expressions"), where an arithmetic item
is wrong for the indicator it hangs off. Every JHS rule matches JHS wording and
computes its own answer; the shared primary rules carry a `veto` for wording
that would make them misfire.

Two rules matter more than the amount:

  * **Generated is labelled.** Each item carries `source: "generated:<rule>"`,
    and the build script keeps authored items in their own file, so nothing
    hand-written is ever overwritten and a teacher can see which is which.
  * **A rule only fires on a matching indicator.** The trigger is the served
    indicator text; an indicator no rule matches gets no questions, and the run
    prints that coverage number rather than padding it.

    python3 scripts/generate_question_bank.py                    # report
    python3 scripts/generate_question_bank.py --apply            # write files
    python3 scripts/generate_question_bank.py --verify           # committed files match
    python3 scripts/generate_question_bank.py --subject mathematics --apply

`--verify` is the regression guard, and it is what `make check` runs: it
regenerates every file in memory and fails if the committed one differs by a
single character. A rule that starts (or stops) firing — the whole misfire class
this script has been bitten by — cannot reach a teacher unnoticed.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CURRICULUM = ROOT / "data" / "curriculum"
OUT = ROOT / "data" / "questions"

# Only mathematics: every rule below answers with arithmetic this script can
# check, which is what makes a generated bank defensible. A language or science
# rule would need a human author, so those subjects stay authored-only.
GENERATED_SUBJECTS = ("mathematics",)

# Primary first, JHS second. The split is real, not cosmetic: see `bands` on the
# rules below, and the JHS section at the foot of the rules.
PRIMARY_GRADES = ("B2", "B3", "B4", "B5", "B6")
JHS_GRADES = ("B7", "B8", "B9")
GENERATED_GRADES = PRIMARY_GRADES + JHS_GRADES

ITEMS_PER_INDICATOR = 3


def indicator_text(record: dict) -> str:
    """The text a rule is allowed to fire on: **the indicator alone**.

    Not `cs_desc`. The content standard is the heading above the indicator
    ("…addition, subtraction, multiplication and division of (i) whole numbers
    within 10,000…"), and at JHS it shares almost all of its vocabulary with
    indicators it does not describe. Matching on it made the money rule fire on
    a data-collection indicator (the word "cost" inside "…taking into
    consideration…") and the rounding rule fire on four-digit addition. A rule
    that fires on the wrong question is worse than no question.

    The `\b` boundaries on the rules exist for the same reason: "cedi" is inside
    "preceding", and before the boundary a B7 relation indicator was asked what
    five pens cost.
    """
    return str(record.get("ind_desc") or "").lower()


def up_to(text: str, default: int) -> int:
    """The number range the indicator itself states, e.g. "up to 100,000".

    Following the indicator matters: an item about a six-digit number in an
    indicator that tops out at 10,000 is off the lesson the teacher is teaching.
    """
    match = (re.search(r"up to (?:and from )?([\d][\d,]*)", text)
             # "numbers to 100", "within 1000" — the same range, said another way.
             or re.search(r"(?:numbers|numerals|quantities|counting|and from) to ([\d][\d,]*)", text)
             or re.search(r"within ([\d][\d,]*)", text)
             or re.search(r"between (?:-?[\d,]+) and ([\d][\d,]*)", text))
    if not match:
        return default
    value = int(match.group(1).replace(",", ""))
    return value if value >= 20 else default


# Default ceilings per grade, used when the indicator states no range.
GRADE_CEILING = {"B2": 1000, "B3": 10000, "B4": 10000, "B5": 100000, "B6": 1000000,
                 # B7 counts past a billion ("more than 1,000,000,000"), and the
                 # JHS number work is deliberately large-number arithmetic.
                 "B7": 1_000_000_000, "B8": 1_000_000_000, "B9": 1_000_000_000}

DIGIT_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
               "seven": 7, "eight": 8, "nine": 9}


def ceiling_for(text: str, grade: str) -> int:
    """The number range the indicator itself states — "up to 100,000",
    "four-digit numbers", "more than 1,000,000,000" — else the grade's default.

    Following the indicator matters: an item about a nine-digit number in an
    indicator that tops out at four digits is off the lesson being taught, and
    it is the first thing a teacher would notice.
    """
    stated = up_to(text, 0)
    if stated:
        return stated
    match = re.search(r"\b(one|two|three|four|five|six|seven|eight|nine)-digit", text)
    if match:
        return 10 ** DIGIT_WORDS[match.group(1)] - 1
    match = re.search(r"more than ([\d][\d,]*)", text)
    if match:
        return int(match.group(1).replace(",", "")) * 10 - 1
    return GRADE_CEILING.get(grade, 10000)


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


# ──────────────────────────────────────────────────── JHS rules (B7–B9) ────
# Written for JHS wording, and only where this script can compute the answer.
# Nothing here is arithmetic borrowed from the primary band: at B7–B9 "multiply"
# usually means binomials, and an item that answers the wrong question is worse
# than no item at all. Where the syllabus wants a construction (bisect an angle,
# draw a net, plot a locus) there is no rule on purpose — that is classroom work,
# not a printed question.

def r_jhs_sequences(rng, ctx):
    """Rule-and-pattern questions, built from the formula so the two agree."""
    step = rng.choice([2, 3, 4, 5, 7, 10, 12])
    start = rng.randint(1, 9)
    terms = [step * n + start for n in range(1, 6)]
    nth = rng.randint(7, 9)
    listed = ", ".join(str(v) for v in terms)
    return [
        short(f"Write the next two terms of the sequence: {listed}.",
              f"{step * 6 + start}, {step * 7 + start}", marks=2),
        mcq(f"What is the rule for the sequence {listed}?",
            f"Add {step} to the previous term",
            [f"Add {step + 1} to the previous term", f"Multiply the previous term by {step}",
             f"Subtract {step} from the previous term"]),
        # The formula and the sequence are the same relation, so the answer is
        # the formula's own value — not a guess about a pattern.
        short(f"The nth term of a sequence is given by {step}n + {start}. "
              f"Find the {nth}th term.", step * nth + start, marks=3),
    ]


def r_jhs_algebra_simplify(rng, ctx):
    a, b, c, d = rng.randint(2, 9), rng.randint(2, 9), rng.randint(1, 9), rng.randint(1, 9)
    x, y = rng.randint(2, 9), rng.randint(1, 9)
    p, q = rng.randint(1, 9), rng.randint(1, 9)
    return [
        short(f"Simplify: {a}x + {b}y + {c}x - {d}y",
              linear([(a + c, "x"), (b - d, "y")]), marks=2),
        short(f"Simplify: ({a}x + {x}) + ({c}x + {q})",
              linear([(a + c, "x")], x + q), marks=2),
        short(f"Subtract ({c}x + {q}) from ({a}x + {p}).",
              linear([(a - c, "x")], p - q), marks=2),
    ]


def r_jhs_algebra_expand(rng, ctx):
    """The distributive property, on its own: expanding brackets is a different
    lesson from collecting like terms, and an indicator that names one should not
    be answered with the other."""
    b, d = rng.randint(2, 9), rng.randint(1, 9)
    a, e = rng.randint(2, 5), rng.randint(1, 9)
    return [
        short(f"Expand: {b}(x + {d})", linear([(b, "x")], b * d), marks=2),
        short(f"Expand and simplify: {a}(x + {e}) + {b}x", linear([(a + b, "x")], a * e), marks=3),
        mcq(f"Expand: 3(x + {d})", f"3x + {3 * d}",
            [f"3x + {d}", f"x + {3 * d}", f"{3 * d}x"]),
    ]


def r_jhs_gradient(rng, ctx):
    a, b = rng.randint(1, 6), rng.randint(1, 9)
    x1 = rng.randint(1, 5)
    x2 = x1 + rng.randint(1, 4)
    y1 = a * x1 + b
    y2 = a * x2 + b
    return [
        short(f"Find the gradient of the line joining the points ({x1}, {y1}) and ({x2}, {y2}).",
              a, marks=2),
        short(f"A straight line passes through ({x1}, {y1}) and ({x2}, {y2}). "
              f"Find the equation of the line in the form y = mx + c.",
              f"y = {a}x + {b}" if a != 1 else f"y = x + {b}", marks=3),
        short(f"A straight line passes through ({x1}, {y1}) and has gradient {a}. "
              f"Find the value of y when x = {x2}.",
              a * x2 + b, marks=2),
    ]


def r_jhs_table_of_values(rng, ctx):
    """Ordered pairs and tables of values — the *graphing* half of the relations
    sub-strand, which a sequence question does not answer."""
    a, b = rng.randint(2, 5), rng.randint(1, 9)
    x0 = rng.randint(0, 4)
    y0 = a * x0 + b
    ask = x0 + rng.randint(2, 4)
    return [
        mcq(f"The relation between x and y is y = {a}x + {b}. "
            f"Which of these ordered pairs lies on its graph?",
            f"({x0}, {y0})",
            [f"({x0}, {y0 + 1})", f"({y0}, {x0})", f"({x0 + 1}, {y0 + 1})"]),
        short(f"A table of values for the relation y = {a}x + {b} gives y = {y0} when x = {x0}. "
              f"Find the value of y when x = {ask}.", a * ask + b, marks=2),
    ]


def r_jhs_significant_figures(rng, ctx):
    value = Decimal(rng.choice(["0.0473821", "27.3941", "4.73821", "381.946", "0.0051483"]))
    figures = rng.choice([2, 3, 4])
    places = rng.choice([1, 2, 3])
    return [
        short(f"Express {value} correct to {figures} significant figures.",
              round_sig(value, figures), marks=2),
        short(f"Express {value} correct to {places} decimal place(s).",
              f"{value:.{places}f}", marks=2),
    ]


def r_jhs_index_form(rng, ctx):
    base = rng.choice([2, 3, 4, 5, 6, 7, 10])
    exponent = rng.randint(2, 5)
    value = base ** exponent
    composite = rng.choice([360, 504, 540, 720, 900, 1080, 1260, 1800, 2250])
    return [
        mcq(f"Find the value of {power(base, exponent)}.", num(value),
            [num(base * exponent), num(value + base), num(value - base)]),
        mcq(f"What is the value of {power(base, 0)}?", "1", ["0", str(base), "10"]),
        short(f"Write {num(composite)} as a product of its prime factors, in index form.",
              prime_factorisation(composite), marks=3),
    ]


def r_jhs_laws_of_indices(rng, ctx):
    base = rng.choice([2, 3, 4, 5, 10])
    m, n = rng.randint(4, 7), rng.randint(2, 3)
    product = power(base, m + n)
    distractors = [power(base, m * n), power(base, abs(m - n)), f"{base * (m + n)}"]
    return [
        mcq(f"Simplify {power(base, m)} x {power(base, n)}, leaving your answer in index form.",
            product, [d for d in distractors if d != product]),
        short(f"Simplify {power(base, m + n)} \u00f7 {power(base, n)}, leaving your answer in index form.",
              power(base, m), marks=2),
        short(f"Simplify ({power(base, 2)})^{n}, leaving your answer in index form.",
              power(base, 2 * n), marks=2),
    ]


def r_jhs_exponential_equations(rng, ctx):
    base = rng.choice([2, 3, 5, 10])
    exponent = rng.randint(2, 5)
    return [
        short(f"Solve for x: {power(base, 'x')} = {num(base ** exponent)}.", exponent, marks=2),
    ]


def r_jhs_squares_and_roots(rng, ctx):
    n = rng.randint(11, 30)
    square = n * n
    return [
        short(f"Find the square root of {num(square)}.", n, marks=2),
        # Consecutive integers are never both perfect squares, so square +/- 1
        # and square +/- 2 are safe distractors with no arithmetic needed.
        mcq("Which of these numbers is a perfect square?", num(square),
            [num(square + 1), num(square - 1), num(square + 2)]),
    ]


def r_jhs_sets(rng, ctx):
    a, b = rng.choice([(12, 18), (16, 24), (20, 30), (15, 25), (18, 27), (24, 36), (28, 42)])
    factors_a = {d for d in range(1, a + 1) if a % d == 0}
    factors_b = {d for d in range(1, b + 1) if b % d == 0}
    shared = sorted(factors_a & factors_b)
    together = sorted(factors_a | factors_b)
    return [
        short(f"A is the set of factors of {a} and B is the set of factors of {b}. "
              f"List the members of the intersection of A and B.",
              ", ".join(str(v) for v in shared), marks=2),
        mcq("How many members are in the union of the two sets?", len(together),
            [len(shared), len(together) - 1, len(shared) + 1]),
    ]


def r_jhs_fraction_operations(rng, ctx):
    denominators = [2, 3, 4, 5, 6, 8]
    a = Fraction(rng.randint(1, 5), rng.choice(denominators))
    b = Fraction(rng.randint(1, 5), rng.choice(denominators))
    while b == a:
        b = Fraction(rng.randint(1, 5), rng.choice(denominators))
    whole, part = rng.randint(1, 3), Fraction(rng.randint(1, 5), rng.choice([2, 3, 4]))
    mixed = whole + part
    return [
        short(f"Simplify: {frac(a)} + {frac(b)}", frac(a + b), marks=2),
        short(f"Simplify: {frac(a)} x {frac(b)}", frac(a * b), marks=2),
        short(f"Simplify: {frac(a)} \u00f7 {frac(b)}", frac(a / b), marks=2),
        short(f"Simplify: {whole} {frac(part)} + {frac(b)}", frac(mixed + b), marks=3),
    ]


def r_jhs_ratio(rng, ctx):
    a, b = rng.choice([(2, 3), (3, 4), (2, 5), (3, 5), (4, 5), (5, 6), (3, 7)])
    factor = rng.randint(3, 12)
    return [
        short(f"Express {a * factor}:{b * factor} in its simplest form.", f"{a}:{b}", marks=2),
        short(f"Find the value of x in the proportion {a}:{b} = {a * factor}:x.",
              b * factor, marks=2),
    ]


def r_jhs_simple_interest(rng, ctx):
    principal = rng.choice([200, 500, 800, 1000, 1500, 2000, 2500, 4000])
    rate = rng.choice([5, 8, 10, 12, 15])
    years = rng.randint(2, 4)
    interest = principal * rate * years // 100
    sales = principal * rng.choice([2, 3, 5])
    return [
        short(f"Find the simple interest on GH\u00a2{num(principal)} for {years} years "
              f"at {rate}% per annum.", f"GH\u00a2{num(interest)}", marks=3),
        short(f"A trader marks a bag of maize at GH\u00a2{num(principal)} and allows a discount "
              f"of {rate}%. Find the discount.", f"GH\u00a2{num(principal * rate // 100)}", marks=2),
        short(f"An agent earns a commission of {rate}% on sales of GH\u00a2{num(sales)}. "
              f"Find the commission.", f"GH\u00a2{num(sales * rate // 100)}", marks=2),
    ]


def r_jhs_rate_and_speed(rng, ctx):
    speed = rng.choice([40, 50, 60, 75, 80, 90])
    hours = rng.randint(2, 6)
    books = rng.randint(3, 12)
    each = rng.choice([2, 3, 5, 8, 10, 15])
    return [
        short(f"A car travels {num(speed * hours)} km in {hours} hours. "
              f"Find its average speed in km/h.", f"{num(speed)} km/h", marks=2),
        short(f"A trader sells one book for GH\u00a2{each}. "
              f"Find the cost of {books} of the same book.",
              f"GH\u00a2{num(each * books)}", marks=2),
    ]


def r_jhs_linear_equations(rng, ctx):
    a, x, b = rng.randint(2, 9), rng.randint(2, 12), rng.randint(1, 20)
    word_a, word_x, word_b = rng.randint(2, 6), rng.randint(2, 9), rng.randint(1, 9)
    return [
        short(f"Solve for x: {a}x + {b} = {a * x + b}.", x, marks=3),
        short(f"When a number is multiplied by {word_a} and {word_b} is added to the result, "
              f"the answer is {word_a * word_x + word_b}. Find the number.", word_x, marks=3),
    ]


def r_jhs_substitution(rng, ctx):
    a, b = rng.randint(2, 6), rng.randint(2, 6)
    x, y = rng.randint(2, 9), rng.randint(2, 9)
    length, breadth = rng.randint(3, 15), rng.randint(2, 12)
    return [
        short(f"Evaluate {a}a + {b}b when a = {x} and b = {y}.", a * x + b * y, marks=2),
        short(f"Use the formula P = 2(l + b) to find P when l = {length} cm and b = {breadth} cm.",
              f"{2 * (length + breadth)} cm", marks=2),
    ]


def r_jhs_inequalities(rng, ctx):
    a, x, b = rng.randint(2, 6), rng.randint(2, 8), rng.randint(1, 12)
    limit = a * x + b
    domain = list(range(0, x + 4))
    members = [n for n in domain if a * n + b < limit]
    listed = "{" + ", ".join(str(n) for n in domain) + "}"
    return [
        short(f"Solve the inequality {a}x + {b} < {limit}.", f"x < {x}", marks=2),
        short(f"List the members of the solution set of {a}x + {b} < {limit} from {listed}.",
              ", ".join(str(n) for n in members) or "no member", marks=2),
    ]


def r_jhs_central_tendency(rng, ctx):
    while True:
        values = [rng.randint(2, 20) for _ in range(5)]
        data = sorted(values + [values[0]])
        if len(set(data)) == 5 and data.count(values[0]) == 2 and sum(data) % len(data) == 0:
            break
    mean = sum(data) // len(data)
    middle = (data[2] + data[3]) / 2
    listed = ", ".join(str(n) for n in data)
    return [
        short(f"Find the mean of the following data: {listed}.", mean, marks=2),
        short(f"Find the median of the following data: {listed}.",
              frac(middle), marks=2),
        mcq(f"State the mode of the following data: {listed}.", values[0],
            [n for n in data if n != values[0]]),
        short(f"Find the range of the following data: {listed}.", data[-1] - data[0], marks=1),
    ]


def r_jhs_probability(rng, ctx):
    red, blue, green = rng.randint(2, 6), rng.randint(2, 6), rng.randint(1, 4)
    total = red + blue + green
    bag = f"A bag contains {red} red, {blue} blue and {green} green bottle tops."
    return [
        short(f"{bag} One bottle top is picked at random. Find the probability that it is red.",
              frac(Fraction(red, total)), marks=2),
        short(f"{bag} Two bottle tops are picked one after the other, the first one being "
              f"replaced before the second is picked. Find the probability that both are red.",
              frac(Fraction(red, total) * Fraction(red, total)), marks=3),
        short(f"{bag} Two bottle tops are picked one after the other, without replacement. "
              f"Find the probability that the first is red and the second is blue.",
              frac(Fraction(red, total) * Fraction(blue, total - 1)), marks=3),
    ]


def r_jhs_angles(rng, ctx):
    angle = rng.randint(25, 65)
    first, second = rng.randint(35, 75), rng.randint(30, 70)
    sides = rng.randint(5, 10)
    return [
        mcq(f"Two angles are complementary. One of them is {angle}\u00b0. Find the other.",
            f"{90 - angle}\u00b0", [f"{180 - angle}\u00b0", f"{angle}\u00b0", f"{90 + angle}\u00b0"]),
        short(f"Two of the angles of a triangle are {first}\u00b0 and {second}\u00b0. "
              f"Find the third angle.", f"{180 - first - second}\u00b0", marks=2),
        short(f"Find the sum of the interior angles of a polygon with {sides} sides.",
              f"{(sides - 2) * 180}\u00b0", marks=2),
    ]


def r_jhs_pythagoras(rng, ctx):
    a, b, c = rng.choice([(3, 4, 5), (6, 8, 10), (5, 12, 13), (9, 12, 15),
                          (8, 15, 17), (7, 24, 25), (12, 16, 20)])
    return [
        short(f"In a right-angled triangle the two shorter sides are {a} cm and {b} cm. "
              f"Find the length of the hypotenuse.", f"{c} cm", marks=3),
        short(f"The hypotenuse of a right-angled triangle is {c} cm and one of the shorter "
              f"sides is {a} cm. Find the length of the third side.", f"{b} cm", marks=3),
    ]


def r_jhs_circle(rng, ctx):
    radius = rng.choice([7, 14, 21, 28])
    circumference = 2 * 22 * radius // 7
    area = 22 * radius * radius // 7
    return [
        short(f"A circle has a radius of {radius} cm. Taking pi as 22/7, find its circumference.",
              f"{num(circumference)} cm", marks=2),
        short(f"A circle has a radius of {radius} cm. Taking pi as 22/7, find its area.",
              f"{num(area)} cm\u00b2", marks=3),
    ]


def r_jhs_surface_area(rng, ctx):
    length, width, height = rng.randint(2, 9), rng.randint(2, 9), rng.randint(2, 9)
    cuboid = 2 * (length * width + length * height + width * height)
    prism_length = rng.randint(6, 12)
    # A 3-4-5 right-angled end: two ends of 6 cm2, and a rectangular wrap of
    # (3 + 4 + 5) by the length of the prism.
    prism = 2 * 6 + (3 + 4 + 5) * prism_length
    return [
        short(f"Find the total surface area of a cuboid measuring {length} cm by {width} cm "
              f"by {height} cm.", f"{num(cuboid)} cm\u00b2", marks=3),
        short(f"A triangular prism has ends that are right-angled triangles with sides 3 cm, "
              f"4 cm and 5 cm, and a length of {prism_length} cm. "
              f"Find its total surface area.", f"{num(prism)} cm\u00b2", marks=3),
    ]


def r_jhs_vectors_and_bearings(rng, ctx):
    a, b = rng.choice([(3, 4), (6, 8), (5, 12), (9, 12), (8, 15)])
    magnitude = int((a ** 2 + b ** 2) ** 0.5)
    bearing = rng.choice([45, 63, 120, 150, 210, 305])
    back = bearing + 180 if bearing < 180 else bearing - 180
    return [
        short(f"Find the magnitude of the vector ({a}, {b}).", magnitude, marks=2),
        short(f"The bearing of B from A is {bearing:03d}\u00b0. "
              f"Find the bearing of A from B.", f"{back:03d}\u00b0", marks=2),
        mcq(f"Which of these vectors is perpendicular to ({a}, {b})?", f"({-b}, {a})",
            [f"({a}, {b})", f"({b}, {a})", f"({-a}, {b})"]),
    ]


def r_jhs_transformations(rng, ctx):
    x, y = rng.randint(-6, 6), rng.randint(-6, 6)
    dx, dy = rng.randint(-5, 5) or 1, rng.randint(-5, 5) or 1
    return [
        mcq(f"The point ({x}, {y}) is translated by the vector ({dx}, {dy}). "
            f"Find the coordinates of its image.",
            f"({x + dx}, {y + dy})",
            [f"({x - dx}, {y - dy})", f"({dx}, {dy})", f"({x + dy}, {y + dx})"]),
        mcq(f"Find the image of the point ({x}, {y}) under a reflection in the x-axis.",
            f"({x}, {-y})", [f"({-x}, {y})", f"({-x}, {-y})", f"({y}, {x})"]),
    ]



# ─────────────────────────────────────────────────────────────── the rules ────
# Each rule: (id, regex over the indicator text, builder(rng) -> [question, …]).
# A builder states its own numbers in the prompt and computes the answer.

def r_place_value(rng, ctx):
    # The indicator's own range decides the size: "between 0 and 100" asks about
    # two-digit numbers, "up to 100,000" about five-digit ones. The old floor of
    # 10,000 overrode that and asked B2 what the digit in 9,748 was worth.
    ceiling = max(100, min(ctx["ceiling"], 10 ** 9))
    number = rng.randint(max(10, ceiling // 10), ceiling)
    digits = len(str(number))
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
    ceiling = max(100, min(ctx["ceiling"], 10 ** 9))
    a, b = rng.randint(max(10, ceiling // 10), ceiling), rng.randint(max(10, ceiling // 10), ceiling)
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
    ceiling = max(100, min(ctx["ceiling"], 10 ** 9))
    number = rng.randint(max(100, ceiling // 10), ceiling)
    place, label = rng.choice([(p, label) for p, label in
                               [(10, "ten"), (100, "hundred"), (1000, "thousand"),
                                (10000, "ten thousand"), (100000, "hundred thousand")]
                               if p <= max(10, ceiling // 10)])
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
    n = rng.randint(10, min(999, max(20, ctx["ceiling"])))
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
    # "within 100" means within 100, and the sum stays inside the stated range.
    ceiling = max(20, min(ctx["ceiling"], 10 ** 6))
    a = rng.randint(max(2, ceiling // 4), ceiling - 2)
    b = rng.randint(2, ceiling - a)
    return [short(f"Add: {num(a)} + {num(b)} = ", num(a + b), marks=2)]


def r_subtraction(rng, ctx):
    ceiling = max(20, min(ctx["ceiling"], 10 ** 6))
    a = rng.randint(max(10, ceiling // 2), ceiling)
    b = rng.randint(max(1, a // 4), max(2, a - 1))
    return [short(f"Subtract: {num(a)} - {num(b)} = ", num(a - b), marks=2)]


def r_multiplication(rng, ctx):
    # A "mental strategies" lesson wants numbers a pupil can hold in their head
    # and "simple multiplication" means simple; the indicator says which it is,
    # so the rule reads it rather than printing a five-digit product either way.
    text = ctx["text"]
    if "mental" in text:
        a, b = rng.randint(12, 99), rng.choice([4, 5, 10, 11, 20, 25, 50])
        return [short(f"Multiply: {num(a)} x {b} = ", num(a * b), marks=2)]
    if "simple" in text:
        a, b = rng.randint(2, 20), rng.randint(2, 20)
        return [short(f"Multiply: {num(a)} x {num(b)} = ", num(a * b), marks=2)]
    ceiling = max(100, min(ctx["ceiling"], 10 ** 7))
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
    places = rng.choice([1, 2])
    value = round(rng.uniform(0.1, 99.9), places)
    # "Write 96.0 as a fraction" is a whole number wearing a decimal point.
    if value == int(value):
        value = round(value + 0.5, places)
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


def r_percentage(rng, ctx):
    percent = rng.choice([5, 10, 15, 20, 25, 50])
    of = rng.choice([20, 40, 60, 80, 120, 200])
    value = of * percent / 100
    return [
        short(f"What is {percent}% of {of}?", f"{value:g}", marks=2),
    ]



# ── Primary rules added 2026-09-20: the lessons the first pass read past ──────
# The rules above fire on the words the syllabus uses outright ("add whole
# numbers", "round", "place value"). These fire on the lessons it words
# differently — counting, mental facts, "equal to"/"not equal to", factors and
# squares, integers, patterns in a table, one-step equations — where the answer
# is still arithmetic this script can compute and therefore check. Each pattern
# names the wording of the indicator it belongs to and nothing else; the veto is
# used where one band's words appear in another lesson.

ROMAN_VALUES = ((100, "C"), (90, "XC"), (50, "L"), (40, "XL"), (10, "X"), (9, "IX"),
                (5, "V"), (4, "IV"), (1, "I"))


def to_roman(value: int) -> str:
    out = []
    for amount, numeral in ROMAN_VALUES:
        while value >= amount:
            out.append(numeral)
            value -= amount
    return "".join(out)


def stated_cap(ctx, default: int) -> int:
    """The range the wording itself states: "within 100", "sums up 19", "up to 10,000".

    `ceiling_for` reads "up to <number>" and the grade default; this reads the
    other ways the syllabus names a range, so a B2 indicator that says "within
    100" is not asked about numbers up to the B2 default of 1,000.
    """
    for pattern in (r"within ([\d][\d,]*)", r"sums up (?:to )?([\d][\d,]*)",
                    r"to (\d+) and related"):
        match = re.search(pattern, ctx["text"])
        if match:
            value = int(match.group(1).replace(",", ""))
            if value >= 10:
                return value
    return max(20, min(ctx["ceiling"], default))


def r_counting_sequence(rng, ctx):
    cap = max(200, stated_cap(ctx, 1000))
    step = rng.choice([2, 5, 10, 25, 100])
    start = rng.randrange(40, max(60, cap - 6 * step))
    start -= start % step
    return [
        short(f"Write the number that comes just after {num(start)}.", num(start + 1), marks=1),
        short(f"Write the number that comes just before {num(start)}.", num(start - 1), marks=1),
        short(f"Count on in {num(step)}s: {num(start)}, {num(start + step)}, "
              f"{num(start + 2 * step)}, {num(start + 3 * step)}, ____",
              num(start + 4 * step), marks=2),
    ]


def r_mental_facts(rng, ctx):
    cap = max(10, min(stated_cap(ctx, 19), 20))
    a = rng.randint(3, cap - 3)
    b = rng.randint(3, cap - a)
    total = a + b
    return [
        mcq(f"What is {a} + {b}?", total, [total + 1, total - 1, total + 2]),
        short(f"What is {total} - {b}?", a, marks=1),
        short(f"Use a double to work out {a} + {b}.", total, marks=2),
    ]


def r_equal_not_equal(rng, ctx):
    cap = max(20, min(stated_cap(ctx, 200), 500))
    a = rng.randint(3, cap // 2)
    b = rng.randint(3, cap // 2)
    total = a + b
    wrong = total + rng.choice([1, 2, 3, 5])
    return [
        mcq("Which of these is true?", f"{a} + {b} = {total}",
            [f"{a} + {b} = {wrong}", f"{a} + {b} = {total + 4}", f"{a} + {b} = {total - 3}"]),
        mcq(f"Is the statement {a} + {b} = {wrong} true or false?", "False", ["True"]),
        short(f"Complete the statement: {total} = {a} + ____", b, marks=1),
    ]


def r_add_subtract_within(rng, ctx):
    cap = max(50, stated_cap(ctx, 1000))
    a = rng.randint(cap // 4, cap - 20)
    b = rng.randint(10, max(11, cap - a))
    return [
        short(f"Work out {num(a)} + {num(b)}.", num(a + b), marks=2),
        short(f"Work out {num(a + b)} - {num(b)}.", num(a), marks=2),
        mcq(f"Which of these is the sum of {num(a)} and {num(b)}?", num(a + b),
            [num(a + b + 10), num(a + b - 10), num(a + b + 1)]),
    ]


def r_missing_numbers(rng, ctx):
    cap = max(50, stated_cap(ctx, 1000))
    a = rng.randint(10, cap // 2)
    b = rng.randint(10, cap // 2)
    return [
        short(f"Find the missing number: {num(a)} + ____ = {num(a + b)}.", num(b), marks=2),
        short(f"Find the missing number: ____ - {num(a)} = {num(b)}.", num(a + b), marks=2),
        mcq(f"What number goes in the box? {num(a + b)} = {num(a)} + ?", num(b),
            [num(b + 1), num(b - 1), num(b + 10)]),
    ]


def r_halves_quarters(rng, ctx):
    wholes = rng.choice([1, 2, 3, 4])
    whole = rng.choice([8, 12, 16, 20])
    many = "s" if wholes > 1 else ""
    return [
        short(f"How many halves are there in {wholes} whole{many}?", wholes * 2, marks=1),
        short(f"How many quarters are there in {wholes} whole{many}?", wholes * 4, marks=1),
        short(f"What is one quarter of {whole}?", whole // 4, marks=2),
    ]


def r_roman_numerals(rng, ctx):
    limit = 30 if re.search(r"xxx|up to 30", ctx["text"]) else 100
    value = rng.randint(4, limit)
    other = rng.randint(4, limit)
    landmark = rng.choice([v for v in (5, 10, 20, 40, 50, 90, 100) if v <= limit])
    return [
        short(f"Write {value} in Roman numerals.", to_roman(value), marks=2),
        short(f"Write {to_roman(other)} in Hindu-Arabic (ordinary) numerals.", other, marks=2),
        mcq(f"Which of these is {landmark} in Roman numerals?", to_roman(landmark),
            [to_roman(landmark + 1), to_roman(landmark + 10), to_roman(landmark - 1)]),
    ]


def r_skip_counting(rng, ctx):
    steps = [int(s.replace(",", "")) for s in re.findall(r"([\d][\d,]*)(?:s\b|'s)", ctx["text"])]
    steps = [s for s in steps if s >= 10] or [50, 100]
    step = rng.choice(steps)
    cap = max(step * 20, stated_cap(ctx, ctx["ceiling"]))
    start = rng.randrange(step, max(step * 2 + 1, cap - 8 * step))
    start -= start % step
    return [
        short(f"Skip count: {num(start)}, {num(start + step)}, {num(start + 2 * step)}, "
              f"{num(start + 3 * step)}, ____  —  what is the next number?",
              num(start + 4 * step), marks=2),
        short(f"Skip count backwards in {num(step)}s from {num(start + 6 * step)}: "
              f"{num(start + 6 * step)}, {num(start + 5 * step)}, ____, ____",
              f"{num(start + 4 * step)}, {num(start + 3 * step)}", marks=2),
        mcq(f"Which number is missing? {num(start)}, {num(start + step)}, ____, "
            f"{num(start + 3 * step)}", num(start + 2 * step),
            [num(start + 2 * step + 1), num(start + 2 * step - 1), num(start + 3 * step + 1)]),
    ]


def r_division_facts(rng, ctx):
    b = rng.randint(3, 9)
    quotient = rng.randint(3, 9)
    product = b * quotient
    return [
        mcq(f"What is {product} ÷ {b}?", quotient, [quotient + 1, quotient - 1, product - b]),
        short(f"Work out {product} ÷ {b} = ", quotient, marks=1),
        short(f"{product} oranges are shared equally among {b} children. "
              f"How many oranges does each child get?", quotient, marks=2),
    ]


def r_factor_list(rng, ctx):
    n = rng.randint(12, 50)
    factors = [d for d in range(1, n + 1) if n % d == 0]
    multiple = n * rng.randint(2, 6)
    return [
        short(f"List all the factors of {n}.", ", ".join(str(f) for f in factors), marks=3),
        mcq(f"Which of these is a multiple of {n}?", multiple,
            [multiple + 1, n * 3 + 1, multiple - 2]),
        mcq(f"If {n} is a factor of {multiple}, then {multiple} is a ____ of {n}.",
            "multiple", ["factor", "prime number", "square number"]),
    ]


def r_square_numbers(rng, ctx):
    n = rng.randint(4, 12)
    squares = [i * i for i in range(1, 6)]
    return [
        mcq("Which of these is a square number?", squares[-1],
            [squares[-1] + 1, squares[-1] - 2, squares[-1] + 3]),
        short(f"Write {n * n} as a product of two equal factors.", f"{n} x {n}", marks=2),
        short(f"Continue the pattern of square numbers: "
              f"{', '.join(str(s) for s in squares)}, ____", squares[-1] + 11, marks=2),
    ]


def r_hcf_lcm_primary(rng, ctx):
    a, b = rng.randint(8, 40), rng.randint(8, 40)
    hcf = _gcd(a, b)
    return [
        short(f"Find the HCF of {a} and {b}.", hcf, marks=2),
        short(f"Find the LCM of {a} and {b}.", a * b // hcf, marks=2),
        mcq(f"Which of these is a common factor of {a} and {b}?", hcf,
            [hcf + 1, hcf + 2, hcf + 3]),
    ]


def r_integers(rng, ctx):
    below = rng.randint(2, 20)
    start = rng.randint(1, 4)
    values = rng.sample([-9, -7, -4, -2, 0, 3, 5, 8], 4)
    a, b = rng.randint(-9, 9), rng.randint(2, 9)
    while a + b == 0:
        a = rng.randint(-9, 9)
    if rng.random() < 0.5:
        arithmetic = (f"Work out {a} + {b}.", a + b)
    else:
        arithmetic = (f"Work out {a} - {b}.", a - b)
    if "number line" in ctx["text"] or "sets of integers" in ctx["text"]:
        middle = short("Arrange these integers from smallest to largest: "
                       + ", ".join(str(v) for v in values) + ".",
                       ", ".join(str(v) for v in sorted(values)), marks=2)
    else:
        middle = short(f"Write the next three numbers in the sequence: {start}, {start - 1}, "
                       f"{start - 2}, ____, ____, ____",
                       ", ".join(str(start - 3 - i) for i in range(3)), marks=2)
    return [
        mcq(f"The temperature on a cold morning was {below} °C below zero. "
            f"Which number shows this temperature?",
            f"-{below} °C", [f"{below} °C", "0 °C", f"-{below + 10} °C"]),
        middle,
        short(arithmetic[0], arithmetic[1], marks=2),
    ]


def r_multi_step(rng, ctx):
    crates, per_crate = rng.randint(3, 9), rng.randint(8, 24)
    sold = rng.randint(10, max(11, crates * per_crate - 5))
    left = crates * per_crate - sold
    groups, per_class = rng.randint(2, 6), rng.randint(3, 9)
    total_pencils = groups * per_class
    boxes = rng.choice([d for d in range(2, 6) if total_pencils % d == 0] or [1])
    amount = rng.randint(40, 120)
    books, price = rng.randint(2, 5), rng.randint(3, 9)
    pens, pen_price = rng.randint(2, 5), rng.randint(2, 5)
    spend = books * price + pens * pen_price
    return [
        short(f"A trader bought {crates} crates of {per_crate} eggs each and sold {sold} eggs. "
              f"How many eggs are left?", left, marks=3),
        short(f"A school bought {boxes} boxes of pencils with "
              f"{total_pencils // boxes} pencils in each box. The pencils were shared equally "
              f"among {groups} classes. How many pencils did each class get?", per_class, marks=3),
        short(f"Kofi had GH¢{amount}.00. He bought {books} books at GH¢{price}.00 each and "
              f"{pens} pens at GH¢{pen_price}.00 each. How much money had he left?",
              f"GH¢{amount - spend}.00", marks=3),
    ]


def r_improper_fractions(rng, ctx):
    denom = rng.choice([2, 3, 4, 5, 6, 8])
    whole = rng.randint(1, 4)
    remainder = rng.randint(1, denom - 1)
    numer = denom * whole + remainder
    proper = [f"{rng.randint(1, d - 1)}/{d}" for d in (3, 4, 5, 8)]
    return [
        mcq("Which of these is an improper fraction?", f"{numer}/{denom}",
            [proper[0], proper[1], "1/2"]),
        short(f"Write {numer}/{denom} as a mixed number.",
              f"{whole} {remainder}/{denom}", marks=2),
        short(f"Write {whole} {remainder}/{denom} as an improper fraction.",
              f"{numer}/{denom}", marks=2),
    ]


def r_compare_fractions(rng, ctx):
    denom = rng.choice([3, 4, 5, 6, 8, 10])
    first, second = rng.randint(1, denom - 1), rng.randint(1, denom - 1)
    while second == first:
        second = rng.randint(1, denom - 1)
    bigger, smaller = max(first, second), min(first, second)
    unit = rng.choice([2, 3, 4, 5])
    return [
        mcq(f"Which fraction is greater: {bigger}/{denom} or {smaller}/{denom}?",
            f"{bigger}/{denom}", [f"{smaller}/{denom}", "They are the same"]),
        short("Arrange these fractions from smallest to largest: 1/2, 1/4, 1/8.",
              "1/8, 1/4, 1/2", marks=2),
        mcq("Which of these fractions is the largest?", f"1/{unit}",
            [f"1/{unit + 1}", f"1/{unit + 2}", f"1/{unit + 4}"]),
    ]


def _mixed(numer: int, denom: int) -> str:
    """`7/4` as `1 3/4`, and a whole result as `3`."""
    whole, remainder = divmod(numer, denom)
    if remainder == 0:
        return str(whole)
    if whole == 0:
        return f"{remainder}/{denom}"
    return f"{whole} {remainder}/{denom}"


def r_fraction_add_sub(rng, ctx):
    d1, d2 = rng.choice([(2, 3), (3, 4), (4, 6), (2, 5), (3, 5), (4, 5), (6, 8)])
    n1, n2 = rng.randint(1, d1 - 1), rng.randint(1, d2 - 1)
    # Swap the operands *before* any arithmetic: the subtraction has to stay
    # positive, and computing the answers first then swapping left the printed
    # fraction and the printed answer describing two different sums.
    if n1 * d2 < n2 * d1:
        n1, n2 = n2, n1
    num, den = n1 * d2 + n2 * d1, d1 * d2
    g = _gcd(num, den)
    diff_num, diff_den = n1 * d2 - n2 * d1, d1 * d2
    gd = _gcd(diff_num, diff_den)
    whole = rng.randint(1, 3)
    mix_num = (whole * d1 + n1) * d2 + n2 * d1
    mix_den = d1 * d2
    gm = _gcd(mix_num, mix_den)
    return [
        short(f"Work out {n1}/{d1} + {n2}/{d2}, leaving your answer in its simplest form.",
              _mixed(num // g, den // g), marks=2),
        short(f"Work out {n1}/{d1} - {n2}/{d2}, leaving your answer in its simplest form.",
              _mixed(diff_num // gd, diff_den // gd), marks=2),
        short(f"Work out {whole} {n1}/{d1} + {n2}/{d2}, leaving your answer as a mixed number.",
              _mixed(mix_num // gm, mix_den // gm), marks=3),
    ]


def r_tables_patterns(rng, ctx):
    step = rng.choice([2, 3, 4, 5, 6, 7, 10])
    start = rng.randint(1, 12)
    xs = [1, 2, 3, 4, 5]
    ys = [start + (x - 1) * step for x in xs]
    shown = ", ".join(f"x = {x}: y = {y}" for x, y in zip(xs, ys))
    missing = rng.randint(1, 3)
    partial = ", ".join(f"x = {x}: y = {y}" for i, (x, y) in enumerate(zip(xs, ys))
                        if i != missing)
    broken = list(ys)
    broken[4] = ys[4] + step
    faulty = ", ".join(f"x = {x}: y = {y}" for x, y in zip(xs, broken))
    return [
        short(f"A pattern is shown in a table: {partial}. Which value of y is missing?",
              f"y = {ys[missing]}", marks=2),
        short(f"A pattern is shown in a table: {shown}. What is the value of y when x = 6?",
              f"y = {ys[4] + step}", marks=2),
        short(f"In this table {faulty}, one value is wrong. Which value is wrong, and what "
              f"should it be?", f"x = {xs[4]} should give y = {ys[4]}, not {broken[4]}.", marks=3),
    ]


def r_pattern_rules(rng, ctx):
    step = rng.choice([2, 3, 4, 5, 6, 10, 25])
    start = rng.randint(1, 20)
    seq = [start + i * step for i in range(4)]
    return [
        short(f"Extend the pattern: {', '.join(str(v) for v in seq)}, ____, ____",
              f"{seq[-1] + step}, {seq[-1] + 2 * step}", marks=2),
        short(f"The rule for a pattern is 'add {step}'. The pattern starts at {start}. "
              f"What is the next element after {seq[-1]}?", seq[-1] + step, marks=2),
        short(f"Is {seq[-1] + step + 1} the next element of the pattern "
              f"{', '.join(str(v) for v in seq)}? Explain your answer.",
              f"No. The next element is {seq[-1] + step}, because each element is {step} "
              f"more than the one before it.", marks=3),
    ]


def r_equations_solve(rng, ctx):
    x = rng.randint(4, 20)
    a = rng.randint(2, x - 1)
    b = rng.randint(2, 9)
    return [
        short(f"Solve: n + {a} = {x + a}.", f"n = {x}", marks=2),
        short(f"Solve: m - {a} = {x - a}.", f"m = {x}", marks=2),
        mcq(f"Which value of y makes the equation {b}y = {x * b} true?", x,
            [x + 1, x - 1, x + 2]),
    ]


def r_equations_write(rng, ctx):
    x = rng.randint(6, 30)
    a = rng.randint(2, 12)
    other = rng.randint(2, 9)
    return [
        short(f"A number increased by {a} gives {x + a}. Write this as an equation using n "
              f"for the unknown number.", f"n + {a} = {x + a}", marks=2),
        short(f"Adjoa had some oranges. She sold {a} of them and had {x} left. Write an "
              f"equation using r for the number of oranges she had at first.",
              f"r - {a} = {x}", marks=2),
        short(f"Write a word problem that the equation n + {other} = {x + other} could "
              f"describe.", "Any sensible problem, e.g. 'a number plus ... equals ...'. "
              "The problem must name the unknown the equation solves.", marks=3),
    ]


# ── Primary rules added 2026-09-20: geometry, measurement and data ───────────
# Same discipline as the number rules above: the pattern names the indicator's
# own wording, and where a lesson cannot be answered on paper (fold the paper,
# conduct the experiment, draw the net) the rule stays out and a human writes it.

def r_shape_facts(rng, ctx):
    grade = ctx["grade"]
    text = ctx["text"]
    if grade == "B6":
        return [
            mcq("How many faces has a triangular prism?", 5, [4, 6, 8]),
            mcq("How many edges has a cube?", 12, [6, 8, 9]),
            mcq("A net of a cube is made up of how many squares?", 6, [4, 8, 12]),
        ]
    if grade == "B3":
        return [
            mcq("How many equal sides has a rhombus?", 4, [2, 3, 6]),
            mcq("How many vertices has a square?", 4, [3, 5, 8]),
            mcq("Which of these shapes is a quadrilateral?", "a trapezium",
                ["a triangle", "a pentagon", "a hexagon"]),
        ]
    shape = rng.choice([("pentagon", 5), ("hexagon", 6), ("triangle", 3)])
    solid = rng.choice([("cube", 6), ("cuboid", 6), ("square-based pyramid", 5)])
    two_d = [
        mcq(f"How many sides has a {shape[0]}?", shape[1],
            [shape[1] - 1, shape[1] + 1, shape[1] + 2]),
        mcq(f"How many vertices has a {shape[0]}?", shape[1],
            [shape[1] - 1, shape[1] + 1, shape[1] + 2]),
        mcq("Which of these is true of a circle?", "It has no straight sides",
            ["It has 3 sides", "It has 4 vertices", "It has 5 corners"]),
    ]
    three_d = [
        mcq(f"How many faces has a {solid[0]}?", solid[1],
            [solid[1] - 1, solid[1] + 2, solid[1] + 4]),
        mcq("Which of these 3D objects has no flat face?", "a sphere",
            ["a cube", "a cylinder", "a cone"]),
        mcq("Which of these objects can roll?", "a cylinder",
            ["a cube", "a cuboid", "a square-based pyramid"]),
    ]
    if "2d" in text or "2-d" in text:
        return two_d
    if "3d" in text or "3-d" in text:
        return three_d
    return [two_d[0], three_d[0], three_d[1]]


def r_angle_classify(rng, ctx):
    size = rng.choice([35, 45, 60, 75, 120, 135, 150, 200, 270])
    if size < 90:
        kind = "acute"
    elif size < 180:
        kind = "obtuse"
    else:
        kind = "reflex"
    named = f"{'an' if kind[0] in 'aeiou' else 'a'} {kind} angle"
    if "square corner" in ctx["text"] or "angles which are right angles" in ctx["text"]:
        return [
            mcq("A cut-out square corner is used to check whether an angle is",
                "a right angle", ["an acute angle", "an obtuse angle", "a straight angle"]),
            mcq("Which of these is a right angle?", "90°", ["45°", "120°", "180°"]),
            mcq("Which of these angles is greater than a right angle?", "120°",
                ["60°", "90°", "45°"]),
        ]
    return [
        mcq(f"An angle of {size}° is", named,
            ["an acute angle", "a right angle", "an obtuse angle", "a reflex angle"]),
        mcq("Which of these is an acute angle?", "60°", ["90°", "120°", "180°"]),
        mcq("Which of these is an obtuse angle?", "120°", ["80°", "90°", "45°"]),
    ]


def r_symmetry_lines(rng, ctx):
    shape = rng.choice([("square", 4), ("rectangle", 2), ("equilateral triangle", 3),
                        ("regular pentagon", 5)])
    return [
        mcq(f"How many lines of symmetry has a {shape[0]}?", shape[1],
            [shape[1] + 1, max(1, shape[1] - 1), shape[1] + 2]),
        mcq("Which of these shapes has no line of symmetry?", "a parallelogram",
            ["a square", "a circle", "an equilateral triangle"]),
        mcq("A shape that can be folded into two exactly matching halves has",
            "a line of symmetry", ["a line of symmetry only when it is a square",
                                   "no symmetry", "four lines of symmetry"]),
    ]


def r_number_line_move(rng, ctx):
    start = rng.randint(20, 400)
    steps = rng.randint(3, 40)
    return [
        short(f"Start at {start} on the number line and move {steps} steps to the right. "
              f"At which number do you land?", start + steps, marks=2),
        short(f"Start at {start + steps} on the number line and move {steps} steps to the "
              f"left. At which number do you land?", start, marks=2),
        mcq(f"Which number is {steps} steps to the right of {start}?", start + steps,
            [start + steps + 1, start + steps - 1, start - steps]),
    ]


def r_area_units(rng, ctx):
    length, width = rng.randint(3, 9), rng.randint(2, 7)
    area = rng.choice([12, 18, 20, 24, 36])
    pairs = [(a, area // a) for a in range(2, area // 2) if area % a == 0][:2]
    return [
        short(f"How many 1 cm² squares are needed to cover a rectangle {length} cm long and "
              f"{width} cm wide?", length * width, marks=2),
        mcq("Which unit would you use to measure the area of a classroom floor?",
            "square metres", ["square centimetres", "centimetres", "cubic metres"]),
        short(f"The area of a rectangle is {area} cm². Give two different pairs of length "
              f"and width the rectangle could have.",
              "; ".join(f"{a} cm by {b} cm" for a, b in pairs), marks=3),
    ]


def r_volume_boxes(rng, ctx):
    length, width, height = rng.randint(2, 6), rng.randint(2, 6), rng.randint(2, 4)
    volume = length * width * height
    other = rng.choice([2, 3, 4])
    return [
        short(f"A box is {length} cm by {width} cm by {height} cm. How many 1 cm³ cubes "
              f"fill it?", volume, marks=2),
        mcq(f"Which of these boxes has the same volume as a {length} cm by {width} cm by "
            f"{height} cm box?",
            f"a {height} cm by {width} cm by {length} cm box",
            [f"a {length} cm by {width} cm by {height + 1} cm box",
             f"a {length} cm by {width + 1} cm by {height} cm box",
             f"a {length + 1} cm by {width} cm by {height} cm box"]),
        short(f"The volume of a box is {volume} cm³. Give two different sets of dimensions "
              f"it could have.",
              f"e.g. {length} cm by {width} cm by {height} cm, or 1 cm by {width} cm by "
              f"{volume // width} cm", marks=3),
    ]


def r_surface_area_primary(rng, ctx):
    side = rng.randint(2, 8)
    l, w, h = rng.randint(3, 8), rng.randint(2, 6), rng.randint(2, 5)
    return [
        short(f"Find the surface area of a cube of side {side} cm.", f"{6 * side * side} cm²",
              marks=3),
        short(f"Find the surface area of a cuboid {l} cm by {w} cm by {h} cm.",
              f"{2 * (l * w + l * h + w * h)} cm²", marks=3),
        mcq(f"The surface area of a cube of side 3 cm is", "54 cm²", ["27 cm²", "36 cm²",
                                                                     "18 cm²"]),
    ]


def r_metric_conversions(rng, ctx):
    # One indicator names metre and centimetre, another kilogram and gram as well
    # as litres and millilitres. Asking the first one about grams is the same
    # mistake as asking a length lesson about mass, so the units come from the
    # indicator's own words.
    text = ctx["text"]
    length = rng.randint(2, 9)
    mass = rng.randint(2, 9)
    capacity = rng.randint(2, 9)
    items = []
    if "metre" in text or "centimetre" in text:
        items.append(short(f"How many centimetres are there in {length} metres?",
                           f"{length * 100} cm", marks=2))
    if "kilogram" in text or "gram" in text:
        items.append(short(f"Change {mass * 1000} grams to kilograms.", f"{mass} kg", marks=2))
    if "litre" in text:
        items.append(short(f"How many millilitres are there in {capacity} litres?",
                           f"{capacity * 1000} ml", marks=2))
    if len(items) == 1:
        items.append(short(f"Change {length} m to centimetres.", f"{length * 100} cm", marks=1))
    return items or [
        short(f"How many centimetres are there in {length} metres?", f"{length * 100} cm",
              marks=2),
    ]


def r_time_units(rng, ctx):
    weeks = rng.randint(2, 9)
    years = rng.randint(2, 6)
    hours = rng.randint(2, 6)
    return [
        short(f"How many days are there in {weeks} weeks?", weeks * 7, marks=1),
        short(f"How many months are there in {years} years?", years * 12, marks=1),
        short(f"How many minutes are there in {hours} hours?", hours * 60, marks=2),
    ]


def r_calendar_dates(rng, ctx):
    if ctx["grade"] == "B4":
        return [
            short("Write the date 7 June 2019 in figures in the form dd/mm/yyyy.",
                  "07/06/2019", marks=2),
            short("How many days has September?", 30, marks=1),
            mcq("Which of these months has 28 days in a common year?", "February",
                ["January", "June", "September"]),
        ]
    return [
        short("Arrange these dates in order, earliest first: 3 March 2020, "
              "28 February 2020, 15 March 2020.",
              "28 February 2020, 3 March 2020, 15 March 2020", marks=3),
        short("How many days has April?", 30, marks=1),
        mcq("Which of these months has 31 days?", "January", ["April", "June", "November"]),
    ]


def r_cardinal_directions(rng, ctx):
    if "north- east" in ctx["text"] or "north-east" in ctx["text"]:
        return [
            mcq("Which direction lies halfway between North and East?", "North-East",
                ["North-West", "South-East", "South-West"]),
            short("Which direction is opposite to South-East?", "North-West", marks=1),
            mcq("You are facing West and you turn 45° clockwise. Which direction are you "
                "facing now?", "North-West", ["South-West", "North", "South"]),
        ]
    return [
        mcq("Ama is facing North. She turns 90° clockwise. Which direction is she facing?",
            "East", ["West", "South", "North"]),
        short("Which direction is opposite to West?", "East", marks=1),
        mcq("Kofi walks 200 m North and then 200 m South. Where is he now?",
            "at his starting point",
            ["400 m North of his starting point", "200 m East of his starting point",
             "400 m South of his starting point"]),
    ]


def r_comparing_measures(rng, ctx):
    names = rng.sample(["Ama", "Kofi", "Esi", "Yaw"], 3)
    lengths = rng.sample(range(8, 25), 3)
    order = sorted(zip(names, lengths), key=lambda pair: pair[1])
    return [
        short(f"{names[0]}'s pencil is {lengths[0]} cm long, {names[1]}'s is {lengths[1]} cm "
              f"and {names[2]}'s is {lengths[2]} cm. Whose pencil is the longest?",
              f"{order[-1][0]}'s pencil", marks=1),
        short(f"{names[0]}'s pencil is {lengths[0]} cm long, {names[1]}'s is {lengths[1]} cm "
              f"and {names[2]}'s is {lengths[2]} cm. Whose pencil is the shortest?",
              f"{order[0][0]}'s pencil", marks=1),
        short(f"Arrange these pencils from shortest to longest: {names[0]} {lengths[0]} cm, "
              f"{names[1]} {lengths[1]} cm, {names[2]} {lengths[2]} cm.",
              ", ".join(f"{name} {length} cm" for name, length in order), marks=2),
    ]


def r_regular_polygons(rng, ctx):
    sides = rng.choice([3, 4, 5, 6])
    return [
        mcq("A polygon whose sides are all equal and whose angles are all equal is called",
            "a regular polygon", ["an irregular polygon", "a quadrilateral", "a circle"]),
        short(f"A polygon has {sides} equal sides and {sides} equal angles. Is it a regular "
              f"polygon? Explain your answer.",
              "Yes - all its sides are equal and all its angles are equal, which is the "
              "definition of a regular polygon.", marks=2),
        mcq("Which of these is a regular polygon?", "an equilateral triangle",
            ["an isosceles triangle", "a rectangle 5 cm by 3 cm", "a parallelogram"]),
    ]


def r_quadrilateral_properties(rng, ctx):
    return [
        mcq("Which of these is true of a rectangle?",
            "Its opposite sides are equal and its four angles are right angles",
            ["All four of its sides are equal", "Its diagonals cross at right angles",
             "It has three sides"]),
        mcq("The diagonals of a square", "are equal and bisect each other at right angles",
            ["are not equal", "are parallel to each other", "meet at 45° only"]),
        short("How many right angles has a square?", 4, marks=1),
    ]


# ── Primary rules added 2026-09-20: data and probability ─────────────────────

def r_tally_pictograph(rng, ctx):
    groups = rng.randint(2, 4)
    singles = rng.randint(1, 4)
    per_symbol = rng.randint(2, 6)
    symbols = rng.randint(3, 9)
    return [
        mcq("In a tally chart, four upright lines with one line drawn across them stand for "
            "how many?", 5, [4, 6, 10]),
        short(f"A tally chart shows {groups} groups of five marks and {singles} single marks. "
              f"How many items does the chart record?", groups * 5 + singles, marks=2),
        short(f"In a pictograph, one symbol stands for {per_symbol} pupils. How many pupils "
              f"do {symbols} symbols stand for?", per_symbol * symbols, marks=2),
    ]


def r_graphs_scale(rng, ctx):
    per_symbol = rng.randint(2, 10)
    symbols = rng.randint(3, 9)
    maize, rice, unit = rng.randint(6, 12), rng.randint(2, 5), rng.randint(2, 6)
    return [
        short("In a graph where one symbol stands for one pupil, how many pupils do 7 "
              "symbols stand for?", 7, marks=1),
        short(f"In a pictograph, one symbol stands for {per_symbol} pupils. How many pupils "
              f"do {symbols} symbols stand for?", per_symbol * symbols, marks=2),
        short(f"In a bar graph the bar for maize is {maize} units high and the bar for rice "
              f"is {rice} units high. One unit stands for {unit} pupils. How many more pupils "
              f"chose maize than rice?", (maize - rice) * unit, marks=3),
    ]


def r_graph_features(rng, ctx):
    return [
        mcq("A double bar graph is used to",
            "compare two sets of data side by side",
            ["show one set of data", "show parts of a whole", "show a single total"]),
        short("State two things every bar graph must have.",
              "Any two of: a title, labelled axes, a scale, a key or legend.", marks=2),
        mcq("Which of these must every graph have?", "a title",
            ["a key", "three colours", "a circle shape"]),
    ]


def r_probability_primary(rng, ctx):
    red, blue = rng.randint(2, 5), rng.randint(1, 4)
    return [
        mcq(f"A bag has {red} red balls and {blue} blue balls. One ball is taken out without "
            f"looking. What is the probability that it is blue?",
            f"{blue}/{red + blue}", [f"{red}/{red + blue}", f"{blue}/{red}", "1/2"]),
        short("List all the possible outcomes when a fair coin is tossed twice.",
              "HH, HT, TH, TT", marks=3),
        short("Classify each of these as impossible, possible or certain: (a) it rains "
              "tomorrow (b) a stone thrown into the air falls back down.",
              "(a) possible  (b) certain", marks=2),
    ]


# ── Primary rules added 2026-09-20, second pass ──────────────────────────────
# The first pass read the wording of the lessons the earlier rules had passed
# over; this pass is the corrections its output review turned up. Six rules were
# firing on another lesson's words ("division as inverse of multiplication" was
# asked to multiply; a capacity indicator was asked to convert kilometres), and
# five lessons that need their own arithmetic — multiplication facts, rounding
# decimals, decimals by a whole number, estimating a sum, capacity in litres —
# had no rule at all. Every new rule below exists because an indicator named it.

def r_multiplication_facts(rng, ctx):
    a, b = rng.randint(2, 12), rng.randint(2, 12)
    return [
        short(f"Work out {a} x {b} = ", a * b, marks=1),
        mcq(f"What is {a} x {b}?", a * b,
            [a * b + a, a * b - b, a * b + 1]),
        mcq("Which multiplication fact is correct?", f"{a} x {b} = {a * b}",
            [f"{a} x {b} = {a * b + 1}", f"{a} x {b} = {a * b - 1}",
             f"{a} x {b} = {a * b + b}"]),
    ]


def r_fraction_times_whole(rng, ctx):
    denom = rng.choice([2, 3, 4, 5, 6, 8])
    numer = rng.randint(1, denom - 1)
    whole = rng.randint(2, 12)
    product = numer * whole
    g = _gcd(product, denom)
    multiple = denom * rng.randint(2, 6)
    return [
        short(f"Work out {whole} x {numer}/{denom}. Give your answer in its simplest form.",
              _mixed(product // g, denom // g), marks=2),
        short(f"What is {numer}/{denom} of {multiple}?", multiple // denom * numer, marks=2),
        mcq(f"Which of these is {numer}/{denom} of {denom}?", numer,
            [numer + 1, numer + 2, numer + 3]),
    ]


def r_round_decimals(rng, ctx):
    def one(place_rng):
        whole = place_rng.randint(1, 49)
        # Three decimal places, so rounding to the tenth or the hundredth is a
        # real decision rather than a re-print of the number it was given.
        value = float(f"{whole}.{place_rng.randint(100, 999)}")
        nearest = place_rng.choice([1, 2])
        label = "tenth" if nearest == 1 else "hundredth"
        answer = f"{round(value, nearest):.{nearest}f}"
        wrongs = [f"{round(value + 10 ** -nearest, nearest):.{nearest}f}",
                  f"{round(value - 10 ** -nearest, nearest):.{nearest}f}",
                  f"{value:.3f}"]
        return value, label, answer, [w for w in dict.fromkeys(wrongs) if w != answer][:3]

    value, label, answer, wrongs = one(rng)
    other, other_label, other_answer, _ = one(rng)
    return [
        mcq(f"Round {value:.3f} to the nearest {label}.", answer, wrongs),
        short(f"Round {other:.3f} to the nearest {other_label}.", other_answer, marks=2),
    ]


def r_decimal_add_sub(rng, ctx):
    places = rng.choice([1, 2])
    a, b = round(rng.uniform(1, 40), places), round(rng.uniform(1, 40), places)
    if a < b:
        a, b = b, a
    show = f"{{:.{places}f}}".format
    total = round(a + b, places)
    return [
        short(f"Work out {show(a)} + {show(b)}.", show(total), marks=2),
        short(f"Work out {show(a)} - {show(b)}.", show(round(a - b, places)), marks=2),
        mcq(f"Which of these is the sum of {show(a)} and {show(b)}?", show(total),
            [show(round(total + 10 ** -places, places)),
             show(round(total - 10 ** -places, places)),
             show(round(total + 1, places))]),
    ]


def r_decimal_times_whole(rng, ctx):
    value, whole = round(rng.uniform(0.5, 9.9), 1), rng.randint(2, 9)
    if value == int(value):     # 6.0 is a whole number wearing a decimal point
        value = round(value + 0.5, 1)
    product = round(value * whole, 1)
    return [
        short(f"Work out {value} x {whole}.", f"{product:g}", marks=2),
        mcq(f"What is {value} x {whole}?", f"{product:g}",
            [f"{round(product + 0.1, 1):g}", f"{round(product - 0.1, 1):g}",
             f"{round(value + whole, 1):g}"]),
    ]


def r_estimation(rng, ctx):
    place = rng.choice([10, 100])
    low, high = (120, 880) if place == 10 else (1200, 8800)
    a, b = rng.randint(low, high), rng.randint(low, high)
    est_a, est_b = int(round(a / place) * place), int(round(b / place) * place)
    label = "ten" if place == 10 else "hundred"
    return [
        short(f"Estimate the sum of {num(a)} and {num(b)} by rounding each number to the "
              f"nearest {label}. Give the estimated sum.",
              f"about {num(est_a + est_b)}  ({num(est_a)} + {num(est_b)})", marks=3),
        short(f"Estimate the difference between {num(a)} and {num(b)} by rounding each number "
              f"to the nearest {label}.",
              f"about {num(abs(est_a - est_b))}  ({num(max(est_a, est_b))} - "
              f"{num(min(est_a, est_b))})", marks=3),
    ]


def r_data_sources(rng, ctx):
    return [
        mcq("Data that you collect yourself by counting or measuring is called",
            "first-hand data", ["second-hand data", "grouped data", "categorical data"]),
        mcq("Data taken from a newspaper or an Internet page is called",
            "second-hand data", ["first-hand data", "tally data", "measured data"]),
        short("Give one example of second-hand data you can find in a newspaper or on the "
              "Internet.",
              "Any correct example, e.g. last month's rainfall figures, election results, "
              "national population figures.", marks=2),
    ]


def r_simplify_fractions(rng, ctx):
    denom, factor = rng.choice([4, 6, 8, 9, 10, 12]), rng.randint(2, 6)
    numer = rng.randint(1, denom - 1)
    top, bottom = numer * factor, denom * factor
    g = _gcd(top, bottom)
    simplest = _mixed(top // g, bottom // g)
    return [
        short(f"Write {top}/{bottom} in its simplest form.", simplest, marks=2),
        mcq(f"Which of these is {top}/{bottom} in its simplest form?", simplest,
            [f"{top - 1}/{bottom - 1}", f"{numer}/{denom + 1}", f"{top}/{bottom - factor}"]),
        short(f"Simplify {top}/{bottom} by dividing the numerator and the denominator by "
              f"their HCF.", simplest, marks=2),
    ]


def r_capacity_volume(rng, ctx):
    cubic, litres = rng.randint(1, 9), rng.randint(2, 9)
    return [
        short(f"How many litres are there in {cubic} m\u00b3? (1 m\u00b3 = 1000 litres)",
              f"{cubic * 1000} litres", marks=2),
        short(f"A tank holds {litres * 1000} litres. What is its volume in cubic metres?",
              f"{litres} m\u00b3", marks=2),
        mcq("Which of these has the greater capacity?", "1 m\u00b3 of water",
            ["1 litre of water", "500 millilitres of water",
             "1 cubic centimetre of water"]),
    ]


def r_ratio_primary(rng, ctx):
    a, b = rng.randint(2, 9), rng.randint(2, 9)
    while a == b:
        b = rng.randint(2, 9)
    g = _gcd(a, b)
    factor = rng.randint(2, 5)
    boys_ratio, girls_ratio = rng.randint(2, 5), rng.randint(2, 5)
    girls = girls_ratio * rng.randint(2, 6)
    boys = boys_ratio * (girls // girls_ratio)
    return [
        short(f"Express the ratio {a * factor} : {b * factor} in its simplest form.",
              f"{a // g} : {b // g}", marks=2),
        short("A drawing uses a scale of 1 : 200. A wall measures 5 cm on the drawing. "
              "How long is the wall in reality? Give your answer in metres.",
              "5 x 200 = 1,000 cm = 10 m", marks=3),
        short(f"The ratio of boys to girls in a class is {boys_ratio} : {girls_ratio}. "
              f"There are {boys} boys. How many girls are there?", f"{girls} girls", marks=3),
    ]


# ── Primary rules added 2026-09-20, third pass ───────────────────────────────
# The first two passes wrote rules for the wording they could read at a glance;
# this pass answers, one indicator at a time, the B2–B6 lessons that were still
# left with no question. Where the syllabus asks a pupil to draw, fold, weigh or
# administer something there is deliberately still no rule — that work is
# classroom work, and the hand-off names it instead of faking it here.

def r_nonstandard_units(rng, ctx):
    """Measuring with tens and ones, and comparing measurements."""
    tens, ones = rng.randint(1, 9), rng.randint(1, 9)
    first, second = rng.randint(5, 12), rng.randint(1, 4)
    return [
        short(f"A rope is {tens} ten-sticks and {ones} unit-sticks long. "
              f"How many unit-sticks long is the rope?", tens * 10 + ones, marks=2),
        mcq(f"Which number is {tens} tens and {ones} ones?", tens * 10 + ones,
            [tens + ones, tens * 10 + ones + 10, tens * 10 - ones]),
        short(f"A table is {first} hand-spans long. A book is {second} hand-spans long. "
              f"How many hand-spans longer is the table than the book?",
              first - second, marks=1),
    ]


SHAPES_BY_SIDES = ((3, "triangle"), (4, "quadrilateral"), (5, "pentagon"),
                   (6, "hexagon"), (8, "octagon"))


def with_article(word: str) -> str:
    """'an octagon', 'a pentagon' — printed prose, so the article has to agree."""
    return f"{'an' if word[0] in 'aeiou' else 'a'} {word}"


def r_shape_from_attributes(rng, ctx):
    """Name the 2D shape the stated number of sides and vertices describes."""
    sides, name = rng.choice(SHAPES_BY_SIDES)
    others = [n for s, n in SHAPES_BY_SIDES if n != name]
    return [
        mcq(f"Which 2D shape has {sides} sides and {sides} vertices?", with_article(name),
            [with_article(other) for other in rng.sample(others, 3)]),
        short(f"A shape has {sides} sides and {sides} vertices. What is the name of the shape?",
              name, marks=2),
        mcq(f"How many vertices has {with_article(name)}?", sides,
            [sides - 1, sides + 1, sides + 2]),
    ]


def r_movement_length(rng, ctx):
    """Moving or turning a shape does not change its length."""
    length = rng.randint(4, 30)
    return [
        short(f"A stick is {length} cm long. It is turned to lie in a different direction. "
              f"How long is the stick now?", f"{length} cm", marks=1),
        mcq(f"Two identical pencils are {length} cm long. One is placed across the desk and "
            f"the other stands upright. Which of these is true?",
            "Both pencils are still the same length",
            ["The upright pencil is longer", "The pencil across the desk is longer",
             "The two pencils now have different lengths"]),
        short(f"A ribbon {length + 6} cm long is moved to another part of the table. "
              f"What is its length now?", f"{length + 6} cm", marks=1),
    ]


def r_opposite_values(rng, ctx):
    """Situations with opposite directions or values."""
    n = rng.randint(2, 20)
    return [
        short(f"A car travels {n} km to the east and then {n} km to the west. "
              f"How far is it from where it started?",
              "0 km — it is back where it started", marks=2),
        mcq("Which of these describes two opposite values?",
            f"{n} steps forward and {n} steps backward",
            [f"{n} steps forward and {n + 2} steps forward", "0 and 1",
             f"{n} and {n}"]),
        short(f"A lift goes up {n} floors and then down {n} floors. Where is the lift now?",
              "on the floor where it started", marks=2),
    ]


def r_commutativity(rng, ctx):
    """The order in which you add does not change the sum."""
    a, b = rng.randint(11, 60), rng.randint(11, 60)
    return [
        mcq("Which of these shows the commutative property of addition?",
            f"{a} + {b} = {b} + {a}",
            [f"{a} + {b} = {a + b}", f"{a} + {b} = {a} + {b + 1}",
             f"{a} - {b} = {b} - {a}"]),
        short(f"Work out {a} + {b}.", a + b, marks=1),
        short(f"Work out {b} + {a}. What does this show about the order of the numbers you add?",
              f"{a + b} — the order does not change the sum", marks=2),
    ]


def r_unit_fraction(rng, ctx):
    """One part of a whole divided into equal parts, a group, or a number line."""
    denom = rng.choice([2, 3, 4, 5, 6, 8, 10])
    group = denom * rng.randint(2, 6)
    mark = rng.randint(1, denom - 1)
    others = [d for d in (2, 3, 5, 6, 8, 10) if d != denom]
    return [
        mcq(f"A whole is divided into {denom} equal parts. What fraction is one part?",
            f"1/{denom}", [f"1/{d}" for d in rng.sample(others, 2)] + [f"{denom}/1"]),
        short(f"What is 1/{denom} of {group}?", group // denom, marks=2),
        short(f"On a number line from 0 to 1 the whole is divided into {denom} equal parts. "
              f"What fraction is reached after counting {mark} of the parts?",
              f"{mark}/{denom}", marks=2),
    ]


def r_quadrilateral_types(rng, ctx):
    """Recognising rhombuses, parallelograms, trapeziums, rectangles and squares."""
    kinds = [
        ("quadrilateral", "a flat shape with 4 straight sides"),
        ("parallelogram", "a quadrilateral with both pairs of opposite sides parallel"),
        ("trapezium", "a quadrilateral with only one pair of opposite sides parallel"),
        ("rhombus", "a quadrilateral with all 4 sides equal"),
        ("rectangle", "a quadrilateral with 4 right angles"),
    ]
    name, meaning = rng.choice(kinds)
    others = [n for n, _ in kinds if n != name]
    return [
        mcq(f"Which name describes {meaning}?", f"a {name}",
            [f"a {other}" for other in rng.sample(others, 3)]),
        mcq("Which of these is NOT a quadrilateral?", "a triangle",
            ["a square", "a trapezium", "a rhombus"]),
        mcq("Which of these has 4 equal sides and 4 right angles?", "a square",
            ["a rhombus", "a parallelogram", "a trapezium"]),
    ]


def r_measure_referents(rng, ctx):
    """Choosing units and referents for length, mass and capacity."""
    text = ctx["text"]
    length = [
        mcq("Which unit would you use to measure the length of your exercise book?",
            "centimetres", ["metres", "kilograms", "litres"]),
        mcq("Which unit would you use to measure the length of a classroom?",
            "metres", ["centimetres", "grams", "millilitres"]),
        short("Name something in your school that is about 1 metre long.",
              "Any sensible referent, e.g. a metre rule, the width of a doorway, the height "
              "of a desk.", marks=2),
    ]
    mass_volume = [
        mcq("Which unit would you use to measure the mass of a bag of rice?",
            "kilograms", ["grams", "metres", "litres"]),
        mcq("Which unit would you use to measure the water in a bucket?",
            "litres", ["kilograms", "centimetres", "grams"]),
        short("Name something in your school whose mass is about 1 kilogram.",
              "Any sensible referent, e.g. a bag of sugar, a full water bottle, a textbook.",
              marks=2),
    ]
    if "metre" in text or "centimetre" in text:
        return length
    return mass_volume


def r_data_method(rng, ctx):
    """Choosing how to collect and record data."""
    return [
        mcq("You want to find out how many pupils in your class walk to school. "
            "Which is the best way to collect the data?",
            "Ask each pupil and record the answers",
            ["Measure each pupil with a tape", "Read it from a newspaper",
             "Guess the number"]),
        mcq("Which is the best way to record how many pupils chose each of four fruits?",
            "a tally chart", ["a number line", "a protractor", "a clock"]),
        short("You want to find out the favourite game of every pupil in your class. "
              "Describe how you would collect and record the data.",
              "Ask every pupil (a survey or questionnaire), then record the answers in a tally "
              "chart or a table.", marks=3),
    ]


def r_fraction_examples(rng, ctx):
    """Fractions in everyday life."""
    return [
        short("Give one example from everyday life where a fraction is used.",
              "Any sensible example, e.g. half a loaf of bread, a quarter of an orange, "
              "half of the class.", marks=2),
        mcq("Which of these is an example of a fraction used in everyday life?",
            "half a loaf of bread", ["three pencils", "a 30 cm ruler", "two hours"]),
        short("Write a short sentence that uses the fraction 1/2.",
              "Any sensible sentence, e.g. 'I ate half of the orange.'", marks=2),
    ]


def r_table_from_problem(rng, ctx):
    """Turning the information in a problem into a table."""
    rate = rng.randint(2, 9)
    weeks = 5
    values = [rate * w for w in range(1, weeks + 1)]
    missing_week = rng.randint(2, weeks - 1)
    shown = ", ".join(f"week {w}: GH¢{values[w - 1]}.00" if w != missing_week
                      else f"week {w}: ____" for w in range(1, weeks + 1))
    return [
        short(f"A pupil saves GH¢{rate}.00 every week. Copy and complete the table: {shown}.",
              f"week {missing_week} = GH¢{values[missing_week - 1]}.00", marks=2),
        short(f"The same pupil saves GH¢{rate}.00 every week. How much is saved in week 7?",
              f"GH¢{rate * 7}.00", marks=2),
        mcq("Which heading belongs in the second column of a table showing the amount "
            "saved each week?", "Amount saved (GH¢)",
            ["Number of pupils", "Length (cm)", "Mass (kg)"]),
    ]


def r_place_value_parts(rng, ctx):
    """Writing a number from its named place-value parts."""
    places = [(100000, "hundred-thousands"), (10000, "ten-thousands"),
              (1000, "thousands"), (100, "hundreds"), (10, "tens"), (1, "ones")]
    if ctx["ceiling"] < 10 ** 6:
        places = places[1:]
    parts = [rng.randint(1, 9) for _ in places]
    number = sum(d * value for d, (value, _name) in zip(parts, places))
    shown = ", ".join(f"{d} {name}" for d, (_value, name) in zip(parts, places))
    return [
        short(f"Write the number that has {shown}.", num(number), marks=2),
        short(f"How many {places[0][1]} are there in {num(number)}?", parts[0], marks=1),
        mcq(f"Which number has {parts[0]} {places[0][1]} and {parts[-1]} ones?",
            num(number), [num(number + 10), num(number - 1), num(number + 100)]),
    ]


def r_integer_stories(rng, ctx):
    """Adding and subtracting with positive and negative values."""
    a, b = rng.randint(3, 20), rng.randint(1, 15)
    depth = a - b
    diver = (f"{depth} m below sea level" if depth > 0
             else ("at sea level" if depth == 0 else f"{-depth} m above sea level"))
    return [
        short(f"The temperature at dawn was -{a} °C. By midday it had risen by {b} °C. "
              f"What was the temperature at midday?", f"{b - a} °C", marks=2),
        short(f"A diver is {a} m below sea level and then rises {b} m. "
              f"At what depth is the diver now?", diver, marks=2),
        mcq(f"Which sum gives -{a}?", f"-{a + b} + {b}",
            [f"-{a} + {b}", f"{a} - {b} + 1", f"-{a + b}"]),
    ]


def r_pattern_rule_words(rng, ctx):
    """Describing a pattern's rule in words."""
    start, step = rng.randint(2, 12), rng.randint(2, 9)
    sequence = ", ".join(str(start + i * step) for i in range(4))
    return [
        short(f"Write the rule for this pattern in words: {sequence}, ____",
              f"add {step} each time", marks=2),
        mcq(f"The pattern {sequence} follows which rule?",
            f"add {step} each time",
            [f"add {step + 1} each time", f"subtract {step} each time",
             f"multiply by {step} each time"]),
        short(f"The rule for a pattern is 'add {step}'. The pattern starts at {start}. "
              f"What is the third element of the pattern?", start + 2 * step, marks=2),
    ]


def r_expression_phrases(rng, ctx):
    """Algebraic expressions written from words."""
    n = rng.randint(3, 12)
    return [
        short(f"Write an expression for 'a number n increased by {n}'.", f"n + {n}", marks=2),
        short(f"Write an expression for '{n} more than a number y'.", f"y + {n}", marks=2),
        mcq("Which of these is an algebraic expression?", f"n + {n}",
            [f"{n} + {n + 1}", f"{n}", f"{n + 2} - 1"]),
    ]


def r_equation_from_picture(rng, ctx):
    """A picture or a balance written as an equation."""
    n, loose = rng.randint(3, 15), rng.randint(2, 9)
    total = n + loose
    return [
        short(f"A balance is level. One side has a bag of n counters and {loose} loose "
              f"counters; the other side has {total} counters. Write an equation and say "
              f"what n is.", f"n + {loose} = {total}, so n = {n}", marks=3),
        short(f"A cup contains x stones. {loose} more stones are added and there are now "
              f"{total}. Write this as an equation using x.", f"x + {loose} = {total}", marks=2),
        mcq(f"Which equation matches this picture: a bag of p balls and {loose} balls "
            f"together make {total} balls?",
            f"p + {loose} = {total}",
            [f"p - {loose} = {total}", f"{loose} - p = {total}", f"p + {total} = {loose}"]),
    ]


def r_equation_meaning(rng, ctx):
    """Saying in words what a one-step equation means."""
    n, step = rng.randint(5, 25), rng.randint(2, 12)
    return [
        short(f"Explain in words what the equation x + {step} = {n + step} means.",
              f"A number x plus {step} equals {n + step}, so x is {step} less than "
              f"{n + step}, which is {n}.", marks=3),
        mcq(f"What does the equation y - {step} = {n} tell you about y?",
            f"y is {step} more than {n}",
            [f"y is {step} less than {n}", f"y is {n} times {step}", f"y equals {step}"]),
        short(f"A pupil says the equation m + {step} = {n + step} means 'take {step} away "
              f"from {n + step}'. Is the pupil right? Explain.",
              f"Yes — the number added is {step}, so {n + step} minus {step} gives m = {n}.",
              marks=2),
    ]


def r_problem_to_equation(rng, ctx):
    """Naming the unknown, writing the equation, then solving it."""
    unknown, step = rng.randint(10, 40), rng.randint(3, 9)
    return [
        short(f"Adjoa had some mangoes. She sold {step} of them and had {unknown} left. "
              f"Let m be the number of mangoes she had at first. Write an equation and "
              f"solve it.", f"m - {step} = {unknown}, so m = {unknown + step}", marks=3),
        short(f"A number is increased by {step} and the result is {unknown}. Let n be the "
              f"number. Write an equation and solve it.",
              f"n + {step} = {unknown}, so n = {unknown - step}", marks=3),
        short(f"Kwame has y pens. He buys {step} more and now has {unknown} pens. Write an "
              f"equation for y and solve it.",
              f"y + {step} = {unknown}, so y = {unknown - step}", marks=3),
    ]


def r_reflection_coordinates(rng, ctx):
    """The image of a point under a reflection, and under a translation."""
    x, y = rng.randint(1, 6), rng.randint(1, 6)
    items = [
        short(f"A point is at ({x}, {y}). It is reflected in the y-axis. What are the "
              f"coordinates of its image?", f"(-{x}, {y})", marks=2),
        short(f"A point is at ({x}, {y}). It is reflected in the x-axis. What are the "
              f"coordinates of its image?", f"({x}, -{y})", marks=2),
    ]
    if "translation" in ctx["text"]:
        dx, dy = rng.randint(1, 5), rng.randint(1, 5)
        items.append(short(
            f"A triangle has a vertex at ({x}, {y}). The triangle is translated {dx} "
            f"{'unit' if dx == 1 else 'units'} to the right and {dy} "
            f"{'unit' if dy == 1 else 'units'} up. What are the coordinates of the image "
            f"of that vertex?", f"({x + dx}, {y + dy})", marks=2))
    else:
        items.append(mcq(f"A shape is reflected in the y-axis and its image is at ({x}, {y}). "
                         f"Where was the shape?", f"(-{x}, {y})",
                         [f"({x}, {y})", f"({x}, -{y})", f"(-{x}, -{y})"]))
    return items


def r_graph_attributes(rng, ctx):
    """The attributes a line graph needs, and when data suits a line graph."""
    second = (short("A table shows the number of pupils in each of five classes. Is this "
                    "continuous data or discrete data? Explain your answer.",
                    "Discrete — the number of pupils is counted, not measured, so the points "
                    "should not be joined with a line.", marks=3)
              if "continuous data" in ctx["text"]
              else mcq("Which set of data is best shown with a line graph?",
                       "the temperature recorded every hour of a day",
                       ["the number of pupils in each class", "the favourite colour of each "
                        "pupil", "the types of fruit sold in a shop"]))
    return [
        mcq("Which of these must every line graph have?",
            "a title, labelled axes and a suitable scale",
            ["a protractor", "a compass", "a tally chart"]),
        second,
        mcq("A table of values goes from 0 to 60. Which interval is most suitable for the "
            "vertical axis?", "10", ["1", "100", "1,000"]),
    ]


def r_graph_from_table(rng, ctx):
    """Reading a table of values that is to be drawn as a line graph."""
    values = [rng.randint(10, 25)]
    for _ in range(4):
        values.append(values[-1] + rng.randint(2, 12))
    table = ", ".join(f"week {w}: {v}" for w, v in zip(range(1, 6), values))
    return [
        short(f"A table of values reads {table}. These points are plotted and joined with "
              f"a line. What is the value at week 4?", values[3], marks=1),
        short(f"A table of values reads {table}. What is the increase from week 1 to week 5?",
              values[4] - values[0], marks=2),
        short(f"A table of values reads {table}. What is the total of all five values?",
              sum(values), marks=2),
    ]


def r_likelihood(rng, ctx):
    """Impossible, possible or certain — and experiments that produce each."""
    if "design" in ctx["text"]:
        return [
            short("Describe an experiment in which one outcome is certain. Say what the "
                  "outcome is.",
                  "Any sensible answer, e.g. taking a red ball from a bag that holds only "
                  "red balls.", marks=3),
            short("Describe an experiment in which one outcome is impossible.",
                  "Any sensible answer, e.g. rolling a 7 with an ordinary die.", marks=3),
            short("Describe an experiment in which an outcome is possible but not likely.",
                  "Any sensible answer, e.g. rolling a 6 with a fair die.", marks=3),
        ]
    colour, other_one, other_two = rng.sample(["red", "blue", "green", "yellow"], 3)
    return [
        mcq("Which of these events is impossible?", "a fair coin landing on its edge",
            ["a fair coin landing heads", "the sun rising tomorrow",
             "a pupil in the class being younger than 30"]),
        mcq(f"A bag holds only {colour} balls. Which of these events is certain when one "
            f"ball is taken out without looking?",
            f"a {colour} ball is taken out",
            [f"a {other_one} ball is taken out", f"a {other_two} ball is taken out",
             "no ball is taken out"]),
        short("Describe an event that is possible but not certain when a fair die is rolled.",
              "Any sensible answer, e.g. rolling a six, or rolling an odd number.", marks=2),
    ]

RULES = [
    # ── Primary rules added 2026-09-20 ──────────────────────────────────────
    # Each tuple's pattern names the wording of the indicator it belongs to.
    # The `veto` is used where one band's words sit inside another lesson.
    # ── Primary rules, third pass: the wording pass 1 and 2 could not read ──
    ("nonstandard-units", r"non-standard units|how long or how much", r_nonstandard_units, "primary"),
    ("shape-from-attributes", r"based on given attributes|number of sides and vertices", r_shape_from_attributes, "primary"),
    ("movement-length", r"placement or direction of a shape or object does not change its length", r_movement_length, "primary"),
    ("opposite-values", r"opposite directions or values", r_opposite_values, "primary"),
    ("commutativity", r"property of commutativity", r_commutativity, "primary"),
    ("unit-fraction", r"unit fraction|parts of a group of objects, point on a line", r_unit_fraction, "primary"),
    ("quadrilateral-types", r"rhombuses, parallelograms, trapezoids", r_quadrilateral_types, "primary"),
    ("measure-referents", r"referents for metre and centimetre|estimate masses and volumes using referents", r_measure_referents, "primary"),
    ("data-method", r"gather and record data|select a method for collecting data", r_data_method, "primary"),
    ("fraction-examples", r"examples of where fractions are used", r_fraction_examples, "primary"),
    ("table-from-problem", r"translate the information in a given problem into a table", r_table_from_problem, "primary"),
    ("place-value-parts", r"model number quantities up to 1,000,000", r_place_value_parts, "primary"),
    ("integer-stories", r"addition and subtraction problems involving integers", r_integer_stories, "primary"),
    ("pattern-rule-words", r"describe, orally or in writing, a given pattern|mathematical language, such as one more", r_pattern_rule_words, "primary"),
    ("expression-phrases", r"algebraic expressions as mathematical phrases", r_expression_phrases, "primary"),
    ("equation-from-picture", r"pictorial or concrete representation of an equation", r_equation_from_picture, "primary"),
    ("equation-meaning", r"meaning of a given one-step equation", r_equation_meaning, "primary"),
    ("problem-to-equation", r"identify the unknown in a problem", r_problem_to_equation, "primary"),
    ("reflection-coordinates", r"single transformation \(i\.e\. reflection|reflection and translation", r_reflection_coordinates, "primary"),
    ("likelihood", r"impossible, possible, or certain|impossible, possible \(likely or unlikely\), certain", r_likelihood, "primary"),
    ("graph-attributes", r"line graph by determining the common attributes|line graph \(continuous data\) or a series of points", r_graph_attributes, "primary"),
    ("graph-from-table", r"create a line graph by using a given table of values", r_graph_from_table, "primary"),

    ("multiplication-facts", r"basic multiplication facts|multiplication facts", r_multiplication_facts, "primary"),
    ("fraction-times-whole", r"multiplying a whole number by a fraction|multiplying a fraction by whole number|a fraction by a fraction", r_fraction_times_whole, "primary"),
    ("round-decimals", r"round ?decimals to the nearest", r_round_decimals, "both"),
    ("decimal-add-sub", r"addition and subtraction of decimals", r_decimal_add_sub, "primary"),
    ("decimal-times-whole", r"multiplying a decimal", r_decimal_times_whole, "primary"),
    ("estimation", r"estimation strategies|estimate the solution", r_estimation, "primary"),
    ("data-sources", r"second-hand data|print and electronic media", r_data_sources, "primary"),
    ("simplify-fractions", r"simplest form of given fractions", r_simplify_fractions, "primary"),
    ("capacity-volume", r"relationship between capacity and volume|1000litres|capacity of", r_capacity_volume, "primary"),
    ("ratio-primary", r"ratio as a concept|equivalent forms, compare and order ratios|proportion as a comparison|proportional reasoning problems", r_ratio_primary, "primary"),
    ("counting-sequence", r"counting sequence|how many\?|count and estimate quantities", r_counting_sequence, "primary"),
    ("mental-facts", r"mental strategies for basic addition facts|basic addition facts", r_mental_facts, "primary"),
    ("equal-not-equal", r"equal to\"? and \"?not equal to|equal to and not equal to", r_equal_not_equal, "primary"),
    ("add-subtract-within", r"add and subtract within|strategies to do calculation|standard strategy or procedure to do addition|strategies for adding|strategies for subtracting", r_add_subtract_within, "primary"),
    ("missing-numbers", r"missing numbers in", r_missing_numbers, "primary"),
    ("halves-quarters", r"one-half and one-quarter|count in halves and quarters|halves and quarters in a whole", r_halves_quarters, "primary", r"meaning of the fraction"),
    ("roman-numerals", r"roman numeral", r_roman_numerals, "primary"),
    ("skip-counting", r"skip count", r_skip_counting, "primary"),
    ("division-facts", r"basic division fact", r_division_facts, "primary"),
    ("factor-list", r"set of factors|relationship between factors and multiples|factors and multiples", r_factor_list, "primary"),
    ("square-numbers", r"square numbers", r_square_numbers, "primary"),
    ("hcf-lcm-prime", r"using prime factors", r_hcf_lcm_primary, "primary", r"simplest form"),
    ("integers", r"positive and negative|through zero|sets of integers", r_integers, "primary"),
    ("multi-step-problems", r"multi-step word problems|multi step word problems", r_multi_step, "primary"),
    ("improper-fractions", r"improper fractions", r_improper_fractions, "primary", r"like denominators"),
    ("compare-fractions", r"compare and order (?:unit )?fractions", r_compare_fractions, "primary"),
    ("fraction-add-sub", r"unlike and mixed fractions", r_fraction_add_sub, "primary"),
    ("tables-patterns", r"in a given table or chart|table or chart|relationship in a given table", r_tables_patterns, "primary"),
    ("pattern-rules", r"extend a given pattern|pattern rule|subsequent elements|predict subsequent|given number is or is not the next element|increasing and decreasing (?:number )?patterns|rule in words and in algebra", r_pattern_rules, "primary"),
    ("equations-solve", r"solve a given (?:one-step )?equation|solve a given addition or subtraction problem involving", r_equations_solve, "primary"),
    ("equations-write", r"as an equation|create a problem for a given equation|unknown is represented by a letter|symbol is used to represent an unknown", r_equations_write, "primary"),
    ("shape-facts", r"common features or attributes|according to the shape of the faces|rectangular and triangular prisms", r_shape_facts, "primary"),
    ("angle-classify", r"draw and identify angles|angles in the environment|measure given angles with a protractor|square corner|angles which are right angles", r_angle_classify, "primary"),
    ("symmetry-lines", r"lines? of symmetry|to make them symmetrical", r_symmetry_lines, "primary"),
    ("number-line-move", r"distances from any given location on a number line", r_number_line_move, "primary"),
    ("area-units", r"area is measured in square units|referents for the units cm|construct different rectangles for a given area|estimate area by using referents", r_area_units, "primary", r"perimeter"),
    ("volume-boxes", r"sizes of boxes that have the same volume|volume of boxes", r_volume_boxes, "primary"),
    ("surface-area-primary", r"surface area", r_surface_area_primary, "primary"),
    ("metric-conversions", r"relationship between the units metre and centimetre|relationship between the units kilogram|kilogram and gram|litres and millilitres", r_metric_conversions, "primary"),
    ("time-units", r"number of days in a week|seconds to a minute", r_time_units, "primary"),
    ("calendar-dates", r"dates of events|read the calendar|read dates on the calendar", r_calendar_dates, "primary"),
    ("cardinal-directions", r"cardinal points", r_cardinal_directions, "primary"),
    ("comparing-measures", r"comparing three or more items", r_comparing_measures, "primary"),
    ("regular-polygons", r"polygon is regular", r_regular_polygons, "primary"),
    ("quadrilateral-properties", r"properties \(e\.g\. sides, angles|properties of squares and rectangles|sides, angles, and diagonals properties", r_quadrilateral_properties, "primary"),
    ("tally-pictograph", r"tallies, checkmarks|concrete graphs and pictographs", r_tally_pictograph, "primary"),
    ("graphs-scale", r"one-to-one correspondence|many-to-one correspondence", r_graphs_scale, "primary", r"print and electronic media"),
    ("graph-features", r"double bar graphs", r_graph_features, "primary"),
    ("probability-primary", r"possible outcomes of a probability experiment|theoretical probability", r_probability_primary, "primary"),

    ("place-value", r"\bplace value\b|positions? (?:around|in) a given number|values? of (?:the )?digits?", r_place_value, "both"),
    ("read-write-numbers", r"read and write numbers|in figures and in words", r_read_write, "both"),
    ("compare-order", r"compare and order|arrange .*order|order(?:ing)? whole numbers", r_compare, "both", r"fractions?|decimals?|percent|ratios|integers"),
    ("rounding", r"\bround(?:ing)?\b", r_round, "both", r"decimals? to the nearest|significant"),
    ("factors", r"factors of whole numbers|identify the factors|factors? of any", r_factors, "both"),
    ("primes", r"prime numbers? and composite|prime numbers? between", r_prime, "both"),
    ("odd-even", r"even and odd numbers", r_odd_even, "both"),
    ("hcf", r"highest common factor", r_hcf, "both", r"simplest form"),
    ("lcm", r"lowest common multiple|least common multiple", r_lcm, "both"),
    ("multiples", r"multiples of whole numbers|common multiples|multiples of \d", r_multiples, "both"),
    ("addition", r"add(?:ing)? (?:and subtract )?(?:up to )?(?:whole )?numbers|addition of", r_addition, "both", r"algebraic|binomial|expression|inequalit"),
    ("subtraction", r"subtract(?:ing|ion)? (?:whole )?numbers", r_subtraction, "both", r"algebraic|binomial|expression|inequalit"),
    ("multiplication", r"multipl(y|ication)|times table", r_multiplication, "both", r"algebraic|binomial|expression|inequalit|brackets|division|multiplication facts|a fraction by whole number|a whole number by a fraction|a fraction by a fraction|multiplying a decimal"),
    ("division", r"divid(e|ing|es)|division", r_division, "both", r"algebraic|binomial|expression|inequalit|simplest form"),
    ("fraction-of", r"fraction of (?:a )?(?:whole |given )?(?:number|quantity)|find the fraction of", r_fraction_of, "both"),
    ("equivalent-fractions", r"equivalent fractions", r_equivalent_fraction, "both"),
    ("decimals", r"decimal (?:place value|numbers|fractions)|decimals?", r_decimal_place, "both", r"round|addition and subtraction of decimals|multiplying a decimal"),
    ("measurement", r"convert .*(?:kilomet|metre|meter)|\b(?:length|mass|capacity)\b", r_measurement, "both", r"non-standard|placement or direction|capacity|estimate lengths"),
    ("perimeter-area", r"perimeter|area of (?:a )?(?:rectangle|square|triangle)", r_perimeter_area, "both"),
    ("time", r"\btime\b|clock|duration", r_time, "primary"),
    ("money", r"\b(?:money|cedis?|GH¢|costs?|prices?)\b", r_money, "both"),
    ("percentage", r"percentage|per cent|percent", r_percentage, "both"),
    # ── JHS only (B7–B9) ─────────────────────────────────────────────────────
    # Every one of these matches JHS wording, and answers with arithmetic the
    # script computes. Where the syllabus asks for a construction — bisect an
    # angle, draw a net, plot a locus — there is deliberately no rule: that is
    # classroom work, not a printed question.
    # The relations sub-strand splits in two, and the split matters: extending a
    # pattern is not the same lesson as plotting it, and a sequence question on a
    # "locate points on the number plane" indicator is the wrong question.
    ("jhs-sequences", r"extend a given relation|rule for a given relation|relation or rule in a pattern|predict subsequent elements", r_jhs_sequences, "jhs"),
    ("jhs-table-of-values", r"table of values|number plane|ordered pairs|linear relations?|graph of a linear", r_jhs_table_of_values, "jhs"),
    # The veto keeps a like-term question off "multiplication and division of
    # algebraic expressions" — that indicator is a different lesson.
    ("jhs-algebra-expand", r"remove brackets|distributive property|\bexpand\b", r_jhs_algebra_expand, "jhs"),
    ("jhs-algebra-simplify", r"algebraic expressions|collect like terms", r_jhs_algebra_simplify, "jhs", r"multiplication and division of algebraic|multiply and divide algebraic|remove brackets|distributive property|substitute values"),
    ("jhs-gradient", r"gradient of a line|equation of a line", r_jhs_gradient, "jhs"),
    ("jhs-significant-figures", r"significant (?:figures|places)|decimal places", r_jhs_significant_figures, "jhs"),
    ("jhs-index-form", r"index form|powers? of (?:numbers|natural numbers)|zero as its exponent|repeated factors", r_jhs_index_form, "jhs"),
    ("jhs-laws-of-indices", r"laws of indices", r_jhs_laws_of_indices, "jhs"),
    ("jhs-exponential-equations", r"exponential equations", r_jhs_exponential_equations, "jhs"),
    ("jhs-squares-roots", r"perfect squares|square roots", r_jhs_squares_and_roots, "jhs"),
    ("jhs-sets", r"union and intersection|concept of sets|sets of factors", r_jhs_sets, "jhs"),
    ("jhs-fraction-operations", r"unlike and mixed fractions|operations on fractions|dividing a fraction|multiplying a fraction|basic operations on fractions", r_jhs_fraction_operations, "jhs"),
    ("jhs-ratio", r"ratio language|equivalent ratios|proportional reasoning|proportional relationships", r_jhs_ratio, "jhs"),
    ("jhs-simple-interest", r"simple interest|discount|commission", r_jhs_simple_interest, "jhs"),
    ("jhs-rate-speed", r"unit rate|constant speed|unit pricing", r_jhs_rate_and_speed, "jhs"),
    ("jhs-linear-equations", r"linear equations", r_jhs_linear_equations, "jhs"),
    ("jhs-substitution", r"substitute values", r_jhs_substitution, "jhs"),
    ("jhs-inequalities", r"linear inequalities", r_jhs_inequalities, "jhs"),
    ("jhs-central-tendency", r"\bmedian\b|\bmodes?\b|measures of central tendency|ungrouped data", r_jhs_central_tendency, "jhs"),
    ("jhs-probability", r"probability", r_jhs_probability, "jhs"),
    ("jhs-angles", r"complementary angles|sum of angles in any polygon|interior angles|third angle", r_jhs_angles, "jhs"),
    ("jhs-pythagoras", r"pythagorean theorem|hypotenuse", r_jhs_pythagoras, "jhs"),
    ("jhs-circle", r"circumference of a circle", r_jhs_circle, "jhs"),
    ("jhs-surface-area", r"surface area", r_jhs_surface_area, "jhs"),
    ("jhs-vectors-bearings", r"\bbearing|column \(component\) form|magnitude", r_jhs_vectors_and_bearings, "jhs"),
    ("jhs-transformations", r"under translation|under reflection|reflectional", r_jhs_transformations, "jhs"),
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


def frac(value) -> str:
    """`Fraction` as a printed fraction: 3/4, or 2 when it is whole."""
    f = Fraction(value)
    return str(f.numerator) if f.denominator == 1 else f"{f.numerator}/{f.denominator}"


def linear(pairs, const: int = 0) -> str:
    """`[(3, "x"), (-2, "y")], 5` -> "3x - 2y + 5".

    Negative and unit coefficients are formatted the way a teacher writes them,
    because the answer string is what a marking scheme prints.
    """
    parts = []
    for coef, letter in pairs:
        if coef == 0:
            continue
        if coef == 1:
            parts.append(letter)
        elif coef == -1:
            parts.append(f"-{letter}")
        else:
            parts.append(f"{coef}{letter}")
    out = ""
    for part in parts:
        if not out:
            out = part
        elif part.startswith("-"):
            out += f" - {part[1:]}"
        else:
            out += f" + {part}"
    if const:
        if not out:
            return str(const)
        return f"{out} + {const}" if const > 0 else f"{out} - {-const}"
    return out or "0"


def power(base: int, exponent: int) -> str:
    """Index form, written in ASCII so a PDF renders it: 2^3.

    The syllabus prints a superscript; jsPDF's standard fonts do not carry one,
    so the papers this bank feeds write the same value as `2^3`.
    """
    return f"{base}^{exponent}"


def prime_factorisation(n: int) -> str:
    """`360` -> "2^3 x 3^2 x 5", the form the syllabus asks for."""
    parts, d = [], 2
    while d * d <= n:
        count = 0
        while n % d == 0:
            n //= d
            count += 1
        if count:
            parts.append(power(d, count) if count > 1 else str(d))
        d += 1
    if n > 1:
        parts.append(str(n))
    return " x ".join(parts)


def round_sig(value, figures: int) -> str:
    """`4.73821` to 3 significant figures -> "4.74" (Decimal, so no float drift)."""
    d = Decimal(str(value))
    if d == 0:
        return "0"
    return f"{d.quantize(Decimal(1).scaleb(d.adjusted() - figures + 1)):f}"


def rules_for(grade: str) -> list[tuple]:
    """The rules that may fire for a grade: (id, pattern, builder, veto).

    `bands` is the split that matters. A primary rule matching primary wording
    ("multiply whole numbers") must not fire at B7, where the same word turns up
    in "multiplication of binomial expressions"; a JHS rule must not fire at B4.
    A vetO is the narrower version of the same problem inside one band — for
    example rounding is arithmetic at both levels, but not for an indicator that
    asks about decimal places.
    """
    jhs = grade in JHS_GRADES
    rules = []
    for entry in RULES:
        rule_id, pattern, builder = entry[:3]
        bands = entry[3] if len(entry) > 3 else "both"
        veto = entry[4] if len(entry) > 4 else None
        if bands == "primary" and jhs:
            continue
        if bands == "jhs" and not jhs:
            continue
        rules.append((rule_id, pattern, builder, veto))
    return rules


def questions_for(code: str, record: dict, grade: str = "B4") -> list[dict]:
    """Every rule that matches the indicator's text, run deterministically."""
    text = indicator_text(record)
    ctx = {"ceiling": ceiling_for(text, grade), "grade": grade, "text": text}
    out = []
    for rule_id, pattern, builder, veto in rules_for(grade):
        if not re.search(pattern, text):
            continue
        if veto and re.search(veto, text):
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
    ap.add_argument("--verify", action="store_true",
                    help="fail if the committed generated files are not what the rules produce now")
    args = ap.parse_args()

    subjects = args.subject or list(GENERATED_SUBJECTS)
    problems: list[str] = []
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

        payload = {
            "subjectId": subject,
            "grade": grade,
            "generatedBy": "scripts/generate_question_bank.py",
            "items": items,
        }
        path = OUT / subject / f"{grade}.generated.json"
        if args.apply and items:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n",
                            encoding="utf-8")
        if args.verify:
            want = json.dumps(payload, ensure_ascii=False, indent=1) + "\n"
            if not path.exists():
                problems.append(f"{path.relative_to(ROOT)} is missing — run --apply")
            elif path.read_text(encoding="utf-8") != want:
                problems.append(
                    f"{path.relative_to(ROOT)} has drifted from the rules — run --apply "
                    f"and check the diff: a rule firing on the wrong indicator shows up here")

    print(f"\n{total_items} questions for {total_indicators} indicators "
          f"({covered} covered, {total_indicators - covered} left for an author)")
    if problems:
        print(f"\n{len(problems)} problem(s):")
        for problem in problems:
            print(f"  x {problem}")
        return 1
    if args.verify:
        print("\nverified — the committed generated files are exactly what the rules produce")
    if not args.apply and not args.verify:
        print("report only — pass --apply to write data/questions/<subject>/<grade>.generated.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
