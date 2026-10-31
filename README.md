# Offline GATE Mock Test App

An offline-first GATE CS mock-test app built from locally supplied official question papers and answer keys.

## Why it exists

Past papers become more useful when they reproduce the timer, readable response controls, review state, marking rules, and post-test reflection of a real CBT.

## Trust boundary

- Official answer-key tables determine every mark.
- Gemma never decides correctness or changes a score.
- Local Gemma guidance appears only after submission.
- Question papers, answer keys, caches, and attempts stay outside Git.

## Features

- CS-1 and CS-2 paper validation.
- Original-page rendering on a high-contrast reading surface.
- A low-glare desktop workspace with clear action hierarchy.
- Readable MCQ, MSQ, and NAT response controls.
- A 180-minute timer, completion bar, and 65-question state palette.
- Official MCQ negative marking in a structured score dashboard.
- A scannable deductions table for incorrect and unattempted questions.
- Local syllabus guidance with visible loading and completion states.

## Run locally

1. Create and activate a Python virtual environment.
2. Install the packages from `requirements.txt`.
3. Run `ollama run gemma3:1b` once to download the local model.
4. Put matching paper PDFs in `papers/` and key PDFs in `keys/`.
5. Run `python inspect_key.py` to preview answer-key table extraction.
6. Run `python paper_store.py` to build the local index.
7. Run `python exam_app.py` to open the CBT.

## Architecture

1. `inspect_key.py` reports the text and tables detected in a local answer-key PDF.
2. `paper_store.py` validates PDF pairs and builds page maps.
3. `ui_theme.py` defines the shared palette, spacing, and widget states.
4. `exam_app.py` renders source pages, records responses, and presents reports.
5. `scoring.py` applies the official answer key and marking rules.
6. `coach.py` sends post-test evidence to local Gemma through Ollama.

## Interface design

The app separates the bright paper surface from a low-glare control workspace. Question-state colours, progress feedback, score cards, and a deductions table make the full exam loop readable without changing the official content.

## Hacktoberfest 2026 entry

Submitted to the Hacktoberfest Open-Source AI Challenge Week 4.

The project turns past GATE papers into active offline practice. Local Gemma keeps post-test guidance private and available without a cloud AI service.

Partner category: Best Use of Gemma.