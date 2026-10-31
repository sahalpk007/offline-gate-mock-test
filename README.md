# Offline GATE Mock Test App

[![Hacktoberfest 2026](https://img.shields.io/badge/Hacktoberfest-2026%20Week%204-ff6b4a?style=flat-square&logo=hacktoberfest)](https://dev.to)
[![Challenge](https://img.shields.io/badge/DEV_Challenge-Open--Source_AI-0a0a0a?style=flat-square&logo=devdotto)](https://dev.to)
[![Category](https://img.shields.io/badge/Partner_Category-Best_Use_of_Gemma-4285F4?style=flat-square&logo=google)](https://ai.google.dev/gemma)
[![Model](https://img.shields.io/badge/LLM-Gemma_3_(1B)-8E44AD?style=flat-square&logo=ollama)](https://ollama.com/library/gemma3)
[![Status](https://img.shields.io/badge/Status-Active_Prototype_%2F_WIP-orange?style=flat-square)](#project-status--wip-disclaimer)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python)](https://www.python.org/)

> **Edge AI / Offline Open-Weight Intelligence**: Transforming static official examination artifacts (PDF question papers and answer keys) into an active, air-gapped Computer-Based Test (CBT) environment powered locally by **Gemma** via **Ollama**—without cloud dependencies, subscriptions, or telemetry.

Submitted to the **Hacktoberfest 2026 Open-Source AI Challenge (Week 4)** on the **DEV Community** for the **Best Use of Gemma** partner category.

---

## Project Status & WIP Disclaimer

> [!IMPORTANT]
> **Active Prototype / Proof of Concept**  
> This project is an auditable, working proof-of-concept built for the Hacktoberfest 2026 challenge. While the core test engine and offline AI coach are operational, certain advanced analytics and historical paper adapters remain in active development.

### What is Fully Functional Today
- **Deterministic Scoring Engine**: Strictly enforces official GATE rules—fractional negative marking for MCQs ($-1/3$ for 1-mark, $-2/3$ for 2-mark), exact-match multiple-select (MSQ) without partial credit, and numerical value tolerances (NAT) with range matching.
- **180-Minute Air-Gapped CBT Interface**: Realistic simulation with a 65-question palette, live status trackers (Answered, Marked for Review, Unattempted), completion progress bar, and high-DPI original-page PDF rendering via PyMuPDF.
- **Local Gemma Coaching & Question Analysis**: Post-submission interactive mentor powered by `gemma3:1b` (via Ollama). Extracts the specific question excerpt from the PDF and provides domain-aware diagnostic coaching, trap analysis, and core theorem proofs.

### In Active Development / Planned for Future Releases
- **Automated Recovery Drill Builder ("Secret Mission")**: Dynamic generation of a personalized 15-question adaptive recovery set targeting weak areas identified during the test.
- **Archival Catalog Ingestion (2021–2025)**: Expand the PDF parser beyond 2026 papers to support historical GATE CS paper formats and OCR variations.
- **Cross-Session Analytics**: Persistent SQLite storage to track historical attempts, weak-topic heatmaps, and pacing analytics over time.

---

## Core Philosophy & Trust Boundary

A core principle of this project is strict architectural separation between **deterministic assessment** and **generative AI coaching**.

```
┌─────────────────────────────────────────────────────────────────┐
│                      TRUST BOUNDARY                             │
│                                                                 │
│  ┌────────────────────────┐         ┌────────────────────────┐  │
│  │  Official Answer Key   │         │    Candidate Attempt   │  │
│  │      Table Data        │         │     Input Responses    │  │
│  └───────────┬────────────┘         └───────────┬────────────┘  │
│              │                                  │               │
│              ▼                                  ▼               │
│      ┌──────────────────────────────────────────────────┐       │
│      │        Deterministic Scoring Engine              │       │
│      │         (Rule-based, zero AI hallucination)      │       │
│      └────────────────────────┬─────────────────────────┘       │
│                               │                                 │
│                      Audited Score & Verdict                    │
│                               │                                 │
└───────────────────────────────┼─────────────────────────────────┘
                                │ (Read-only handover post-test)
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   EDGE AI / COACHING RUNTIME                    │
│                                                                 │
│      ┌──────────────────────────────────────────────────┐       │
│      │             Local Ollama + Gemma 3               │       │
│      │   - Explains trap options on incorrect answers   │       │
│      │   - Proves theorems for unattempted questions    │       │
│      │   - NEVER modifies score, key, or verdict        │       │
│      └──────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

1. **Gemma Never Scores**: The language model has zero authority over grading. Correctness and marks are computed deterministically against the extracted official answer key. Gemma only receives read-only diagnostic data *after* submission.
2. **Defend the Ground Truth**: When explaining a problem, Gemma is constrained to defend and explain the official key—eliminating grading ambiguity and model hallucinations.
3. **Data Privacy & Copyright Respect**:
   - Examination PDFs, generated image caches (`cache/`), and candidate attempt records (`data/`) are kept entirely on your local machine and excluded via `.gitignore`.
   - Complete air-gap operation: no external API keys, telemetry, or network calls are required.

---

## Technical Architecture

The application is structured into modular, single-responsibility components:

```
offline-gate-mock-test/
├── papers/               # Local official question paper PDFs (gitignored)
├── keys/                 # Local official answer key PDFs (gitignored)
├── data/                 # Indexed paper catalog metadata (gitignored)
├── cache/                # Rendered page image cache (gitignored)
│
├── inspect_key.py        # Validates and previews answer-key table extraction
├── paper_store.py        # PDF-to-key mapper and question-page indexer
├── scoring.py            # Deterministic GATE marking & penalty engine
├── coach.py              # Domain classifier, excerpt extractor & Gemma client
├── ui_theme.py           # Accessible, low-glare CBT design system & palette
└── exam_app.py           # Tkinter CBT desktop interface & review workspace
```

### Module Overview

| Module | Purpose | Key Responsibilities |
| :--- | :--- | :--- |
| [`scoring.py`](scoring.py) | **Deterministic Evaluation** | Computes official GATE scores (MCQ negative penalties, MSQ exact matches, NAT float/range tolerances). |
| [`coach.py`](coach.py) | **Local AI Mentorship** | Regex-based syllabus classifier, PyMuPDF question boundary extractor, and local Ollama (`gemma3:1b`) API integration. |
| [`exam_app.py`](exam_app.py) | **CBT Application Shell** | Desktop Tkinter app with 180-min timer, 65-button question palette, response controls, and post-exam review drawer. |
| [`paper_store.py`](paper_store.py) | **Catalog & Page Indexer** | Extracts tabular keys from PDF, indexes question coordinates, and builds `data/papers.json`. |
| [`inspect_key.py`](inspect_key.py) | **Extraction Inspector** | Diagnostic utility to inspect raw table bounding boxes and text extracted from official keys. |
| [`ui_theme.py`](ui_theme.py) | **Design System** | High-contrast reading surface for question papers, low-glare dark chrome, and accessible status tokens. |

---

## Marking Scheme Implementation

The scoring engine strictly matches official GATE (Graduate Aptitude Test in Engineering) guidelines:

| Question Type | Correct | Incorrect | Unattempted | Evaluation Rule |
| :--- | :---: | :---: | :---: | :--- |
| **MCQ** (1 Mark) | $+1.00$ | $-0.33$ | $0.00$ | Single choice option match. Penalty is $-\frac{1}{3}$. |
| **MCQ** (2 Marks) | $+2.00$ | $-0.67$ | $0.00$ | Single choice option match. Penalty is $-\frac{2}{3}$. |
| **MSQ** (1 or 2 Marks) | $+M$ | $0.00$ | $0.00$ | Multiple-select; all correct options required. Zero partial credit, zero penalty. |
| **NAT** (1 or 2 Marks) | $+M$ | $0.00$ | $0.00$ | Numerical answer; parsed as float and checked against exact key or inclusive range (e.g., `12 to 14`). Zero penalty. |

---

## Quickstart & Local Setup

### Prerequisites
- **Python 3.10+**
- **[Ollama](https://ollama.com/)** installed and running on your local machine

### 1. Clone & Set Up Environment
```bash
git clone https://github.com/your-username/offline-gate-mock-test.git
cd offline-gate-mock-test

# Create and activate virtual environment
python -m venv .venv

# Windows:
.venv\Scripts\activate
# Linux/macOS:
# source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Pull the Gemma Model
Make sure Ollama is running, then pull the lightweight **Gemma 3 (1B)** model:
```bash
ollama run gemma3:1b
```
*(You can exit the Ollama chat prompt once the download completes; Ollama's local HTTP API will remain active on port 11434).*

### 3. Add Examination Artifacts
Place your official question paper and key PDFs into their respective folders:
```bash
mkdir -p papers keys cache data

# Example:
# papers/GATE2026_CS_Paper.pdf
# keys/GATE2026_CS_Key.pdf
```

### 4. Index Papers & Run the CBT
```bash
# Preview table extraction from the key
python inspect_key.py

# Build question-page index and paper metadata
python paper_store.py

# Launch the offline mock test app
python exam_app.py
```

---

## How It Works: The Exam Experience

1. **Pre-Exam Initialization**:
   `paper_store.py` matches the paper with its answer key, extracting the 65 question metadata entries (type, marks, official answer) and pre-mapping question numbers to page indices.
2. **Realistic 180-Minute CBT**:
   The desktop UI renders original PDF pages via PyMuPDF at high DPI, preserving complex mathematical notation, circuit diagrams, and pseudocode formatting without conversion artifacts.
3. **Response Management**:
   The 65-question palette tracks response states in real time:
   - 🟢 **Answered**
   - 🟣 **Marked for Review**
   - 🟡 **Answered & Marked for Review**
   - ⚪ **Unattempted**
4. **Deterministic Scorecard**:
   Upon submission, `scoring.py` computes net marks, gross positive marks, deductions, accuracy percentage, and a question-by-question breakdown table.
5. **On-Demand Gemma Coaching**:
   Clicking any question in the deductions table loads the exact question excerpt into Gemma. Gemma diagnoses why the chosen answer failed, highlights standard pitfalls, and outlines the theoretical derivation—all completely offline.

---

## Data Privacy & Copyright

- **No Question Paper Piracy**: This repository distributes no copyrighted question papers or answer keys. Users supply their own official PDFs downloaded directly from official GATE organizing institute portals.
- **Local Git Exclusions**: All PDFs (`papers/`, `keys/`), pre-rendered raster tiles (`cache/`), and test attempt records (`data/`) are explicitly excluded in `.gitignore`.
- **Zero Cloud Leakage**: Neither candidate responses nor question content are transmitted to external servers.

---

## Roadmap

- [x] PyMuPDF-based original PDF page renderer
- [x] Deterministic GATE scoring engine (MCQ, MSQ, NAT)
- [x] Full 65-question interactive palette and 180-minute timer
- [x] Offline Gemma 3 coaching via Ollama
- [ ] **Secret Mission 15**: Adaptive generator for weak-topic 15-question rescue drills
- [ ] Support for legacy paper formats (GATE 2021–2025)
- [ ] SQLite-backed historical progress and retention tracking
- [ ] Custom system prompt adjustments for specialized syllabus domains

---

## License & Acknowledgments

- **License**: Free | Open-Source
- **Contest**: Built for the [Hacktoberfest 2026 Open-Source AI Challenge](https://dev.to/challenges/hacktoberfest-week4-2026-10-26) on DEV.
- **Special Thanks**: The Google Gemma team for open-weight intelligence on the edge, and the PyMuPDF & Ollama communities for open-source developer tooling.
