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
    match = re.search(r"up to (?:and from )?([\d][\d,]*)", text)
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
    ("place-value", r"\bplace value\b|positions? (?:around|in) a given number|values? of (?:the )?digits?", r_place_value, "both"),
    ("read-write-numbers", r"read and write numbers|in figures and in words", r_read_write, "both"),
    ("compare-order", r"compare and order|arrange .*order|order(?:ing)? whole numbers", r_compare, "both", r"fractions?|decimals?|percent"),
    ("rounding", r"\bround(?:ing)?\b", r_round, "both", r"decimals? to the nearest|significant"),
    ("factors", r"factors of whole numbers|identify the factors|factors? of any", r_factors, "both"),
    ("primes", r"prime numbers? and composite|prime numbers? between", r_prime, "both"),
    ("odd-even", r"even and odd numbers", r_odd_even, "both"),
    ("hcf", r"highest common factor", r_hcf, "both"),
    ("lcm", r"lowest common multiple|least common multiple", r_lcm, "both"),
    ("multiples", r"multiples of whole numbers|common multiples|multiples of \d", r_multiples, "both"),
    ("addition", r"add(?:ing)? (?:and subtract )?(?:up to )?(?:whole )?numbers|addition of", r_addition, "both", r"algebraic|binomial|expression|inequalit"),
    ("subtraction", r"subtract(?:ing|ion)? (?:whole )?numbers", r_subtraction, "both", r"algebraic|binomial|expression|inequalit"),
    ("multiplication", r"multipl(y|ication)|times table", r_multiplication, "both", r"algebraic|binomial|expression|inequalit|brackets"),
    ("division", r"divid(e|ing|es)|division of", r_division, "both", r"algebraic|binomial|expression|inequalit"),
    ("fraction-of", r"fraction of (?:a )?(?:whole |given )?(?:number|quantity)|find the fraction of", r_fraction_of, "both"),
    ("equivalent-fractions", r"equivalent fractions", r_equivalent_fraction, "both"),
    ("decimals", r"decimal (?:place value|numbers|fractions)|decimals?", r_decimal_place, "both"),
    ("measurement", r"convert .*(?:kilomet|metre|meter)|\b(?:length|mass|capacity)\b", r_measurement, "both"),
    ("perimeter-area", r"perimeter|area of (?:a )?(?:rectangle|square|triangle)", r_perimeter_area, "both"),
    ("time", r"\btime\b|clock|duration", r_time, "primary"),
    ("money", r"\b(?:money|cedis?|GH¢|costs?|prices?)\b", r_money, "both"),
    ("average", r"average|mean of", r_average, "both"),
    ("percentage", r"percentage|per cent|percent", r_percentage, "both"),
    # ── JHS only (B7–B9) ─────────────────────────────────────────────────────
    # Every one of these matches JHS wording, and answers with arithmetic the
    # script computes. Where the syllabus asks for a construction — bisect an
    # angle, draw a net, plot a locus — there is deliberately no rule: that is
    # classroom work, not a printed question.
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
