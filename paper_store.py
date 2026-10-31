from pathlib import Path
import json
import re

import pymupdf

QUESTION_PATTERN = re.compile(r"Q\.\s*(\d+)")


def extract_answer_rows(key_path):
    # Preserve the official table as the scoring source.
    answers = []

    with pymupdf.open(key_path) as document:
        for page in document:
            tables = page.find_tables()

            for table in tables.tables:
                for row in table.extract():
                    # Remove empty spacer cells inserted by table detection.
                    cells = []
                    for cell in row:
                        value = re.sub(r"\s+", " ", cell or "").strip()
                        if value:
                            cells.append(value)

                    if len(cells) != 6 or not cells[0].isdigit():
                        continue

                    # Convert values such as "CS 1 -" into "CS-1".
                    section = cells[3]
                    session_match = re.search(r"\bCS\s*(\d+)", section)

                    if session_match:
                        section = f"CS-{session_match.group(1)}"

                    answers.append(
                        {
                            "number": int(cells[0]),
                            "type": cells[2],
                            "section": section,
                            "key": cells[4],
                            "marks": int(cells[5]),
                        }
                    )

    return answers


def map_question_pages(paper_path):
    # Keep diagrams intact by pointing to original PDF pages.
    question_pages = {}
    with pymupdf.open(paper_path) as document:
        for page in document:
            text = page.get_text(sort=True)
            for match in QUESTION_PATTERN.finditer(text):
                number = int(match.group(1))
                if 1 <= number <= 65:
                    question_pages[number] = page.number
    return question_pages


def session_from_answers(answers):
    # GA is shared, so use the paper-specific subject label.
    sessions = {
        row["section"]
        for row in answers
        if row["section"].startswith("CS-")
    }
    if len(sessions) != 1:
        raise ValueError("Expected one CS session in the answer key")
    return sessions.pop()


def build_paper_record(paper_path, key_path):
    # Validate the pair before any score can use it.
    answers = extract_answer_rows(key_path)
    # print(f"{key_path}: extracted {len(answers)} answer rows") 
    # print("Sections found:", sorted({repr(row["section"]) for row in answers})) 

    question_pages = map_question_pages(paper_path)
    session = session_from_answers(answers)
    expected = session.replace("-", "")

    if expected not in paper_path.stem.upper():
        raise ValueError(
            f"{paper_path.name} does not match {session}"
        )
    if len(answers) != 65 or len(question_pages) != 65:
        raise ValueError(
            f"Expected 65 answers and pages for {paper_path.name}"
        )

    return {
        "paper": paper_path.as_posix(),
        "key": key_path.as_posix(),
        "session": session,
        "answers": answers,
        "question_pages": question_pages,
    }


def scan_papers():
    # Match every *_Keys.pdf file with the same paper stem.
    records = []
    for key_path in sorted(Path("keys").glob("*_Keys.pdf")):
        stem = key_path.stem.removesuffix("_Keys")
        paper_path = Path("papers") / f"{stem}.pdf"
        if not paper_path.exists():
            raise FileNotFoundError(f"Missing {paper_path}")
        record = build_paper_record(paper_path, key_path)
        records.append(record)
        print(
            f"{stem}: {len(record['answers'])} answers, "
            f"{len(record['question_pages'])} question pages"
        )

    Path("data").mkdir(exist_ok=True)
    Path("data/papers.json").write_text(
        json.dumps(records, indent=2), encoding="utf-8"
    )
    print(f"Saved {len(records)} papers to data/papers.json")


if __name__ == "__main__":
    scan_papers()