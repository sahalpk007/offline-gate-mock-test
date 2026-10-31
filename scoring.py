import re


def normalize_choices(value):
    # Store comparable MCQ and MSQ option strings.
    parts = [part.strip().upper() for part in value.split(";")]
    return ";".join(sorted(part for part in parts if part))


def nat_matches(response, official_key):
    # Accept an exact number or an inclusive official range.
    try:
        value = float(response)
    except ValueError:
        return False

    match = re.fullmatch(
        r"\s*(-?\d+(?:\.\d+)?)\s+to\s+"
        r"(-?\d+(?:\.\d+)?)\s*",
        official_key,
    )
    if match:
        lower, upper = map(float, match.groups())
        return lower <= value <= upper

    try:
        return abs(value - float(official_key)) < 1e-9
    except ValueError:
        return False


def score_question(item, response):
    # Determine correctness before assigning marks.
    if not response:
        return "unattempted", 0.0

    kind = item["type"]
    official = item["key"]
    if kind == "NAT":
        correct = nat_matches(response, official)
    else:
        correct = normalize_choices(response) == normalize_choices(official)

    if correct:
        return "correct", float(item["marks"])
    if kind == "MCQ":
        return "incorrect", -(float(item["marks"]) / 3)
    return "incorrect", 0.0


def score_attempt(answers, responses):
    # Aggregate all 65 official-key decisions.
    questions = []
    for item in answers:
        number = int(item["number"])
        response = responses.get(number, "")
        verdict, points = score_question(item, response)
        questions.append({
            **item, "response": response,
            "verdict": verdict, "points": round(points, 2),
        })

    return {
        "score": round(sum(row["points"] for row in questions), 2),
        "correct": sum(row["verdict"] == "correct" for row in questions),
        "incorrect": sum(row["verdict"] == "incorrect" for row in questions),
        "unattempted": sum(row["verdict"] == "unattempted" for row in questions),
        "questions": questions,
    }


