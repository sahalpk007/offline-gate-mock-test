import json
import re
import urllib.request
import pymupdf

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "gemma3:1b"


def clean_key(raw_key):
    """Normalizes official answer keys (e.g., '6 to 6' -> '6', 'A;C;D' -> 'A, C, D')."""
    if not raw_key:
        return ""
    val = str(raw_key).strip()
    range_match = re.match(r"^\s*([-\d.]+)\s*(?:to\s*([-\d.]+))?\s*$", val)
    if range_match:
        low, high = range_match.group(1), range_match.group(2)
        return low if (high is None or low == high) else f"{low} to {high}"
    return val.replace(";", ", ")


def detect_gate_subject(text):
    """Deterministically identifies the GATE CS syllabus domain from question signatures."""
    t = text.lower()

    if re.search(r"\b(fork\s*\(|process|processes|fcfs|sjf|round robin|scheduling|deadlock|banker|semaphore|mutex|paging|virtual memory|tlb miss|page table)\b", t):
        return "Operating Systems"
    if re.search(r"\b(relational|database|candidate key|superkey|functional dependenc|3nf|bcnf|sql|tuple relational)\b", t):
        return "Databases"
    if re.search(r"\b(tcp|udp|ip address|cidr|subnet|sliding window|congestion|socket|http|routing|ethernet|data link)\b", t):
        return "Computer Networks"
    if re.search(r"\b(pipeline|pipelined|hazard|cache|cache memory|set-associative|tag field|addressing mode|instruction format|ieee 754|alu|microprogrammed)\b", t):
        return "Computer Organization and Architecture"
    if re.search(r"\b(dfa|nfa|finite automata|regular language|regular expression|context-free|cfg|pda|turing machine|undecidab)\b", t):
        return "Theory of Computation"
    if re.search(r"\b(parser|parsing|ll\(1\)|slr|lalr|syntax-directed|sdd|lexical|common subexpression|basic block|intermediate code)\b", t):
        return "Compiler Design"
    if re.search(r"\b(boolean|k-map|minterm|maxterm|flip-flop|counter|multiplexer|logic gate|2's complement)\b", t):
        return "Digital Logic"
    if re.search(r"\b(c program|printf|struct node|singly linked list|binary search tree|bst|heap|minheap|recursion|malloc|binary tree)\b", t):
        return "Programming and Data Structures"
    if re.search(r"\b(asymptotic|worst case|recurrence relation|sorting|hashing|hash table|linear probing|dfs|bfs|spanning tree|mst|shortest path|dijkstra|bellman-ford)\b", t):
        return "Algorithms"
    if re.search(r"\b(matrix|eigenvalue|determinant|null space|rank|probability|random variable|expected value|poisson|normal distribution|predicate|propositional|2-colorable|bipartite|graph|vertices|edges|matching|combinatorics)\b", t):
        return "Engineering Mathematics (Discrete Math & Calculus)"

    return "Computer Science & IT"


def extract_focused_question_text(paper_path, page_number, question_number):
    """Extracts text around the target question to prevent multi-question bleed."""
    with pymupdf.open(paper_path) as doc:
        full_page = doc[page_number].get_text(sort=True)

    current_pat = rf"Q\.?\s*{question_number}\b"
    next_pat = rf"Q\.?\s*{question_number + 1}\b"

    match_current = re.search(current_pat, full_page)
    if match_current:
        start_idx = match_current.start()
        match_next = re.search(next_pat, full_page[start_idx:])
        if match_next:
            return full_page[start_idx : start_idx + match_next.start()].strip()
        return full_page[start_idx : start_idx + 1300].strip()

    return full_page[:1300].strip()


def build_cs_prompt(row, snippet, detected_subject):
    official = clean_key(row["key"])
    candidate = clean_key(row["response"]) if row["response"] else "Unattempted"
    verdict = row["verdict"]

    if verdict == "incorrect" and candidate != "Unattempted":
        focus = (
            f"The candidate marked '{candidate}', which is incorrect.\n"
            f"Explain clearly what trap makes '{candidate}' fail and why '{official}' is the exact correct answer."
        )
    elif verdict == "correct":
        focus = f"The candidate correctly chose '{official}'. Explain the core theorem or rule proving why '{official}' is correct."
    else:
        focus = f"The candidate left this question unattempted. Explain step-by-step how to derive '{official}' from the given rules."

    return f"""You are an authoritative GATE Computer Science mentor. Provide a precise, factual coaching review for Question Q.{row['number']}.
CRITICAL RULE: The official answer key is '{official}'. It is 100% correct. Defend and prove '{official}'. Never contradict the official key.
Use clean plain-text/Unicode for formulas (e.g. O(V + E), x^2, ceil(n/2)). Never use LaTeX $$ syntax.

SUBJECT DOMAIN: {detected_subject}
QUESTION EXCERPT:
{snippet}

DETAILS:
- Question Number: Q.{row['number']}
- Question Type: {row['type']} ({row['marks']} Marks)
- Official Key: {official}
- Candidate: {candidate} ({verdict})

{focus}

Respond strictly following these three exact headings:

**Syllabus Topic Classification:**
{detected_subject} - [Specific 2-4 word subtopic being tested]

**Likely Misconception:**
[State in 1-2 direct sentences the exact technical error, boundary case, or wrong assumption that leads away from '{official}']

**3-Step Revision Advice:**
1. Core Principle: [State the exact theorem, formula, or definition needed for this problem]
2. Verification Shortcut: [State a quick check, elimination method, or standard property for this question type]
3. Targeted Practice: [State the immediate related GATE CS concept to practice next]
"""


def deduplicate_revision(raw_text):
    """
    Detects if Gemma generated a duplicate '1. Core Principle' block
    and keeps only the second, detailed one as requested.
    """
    pattern = re.compile(
        r"(?:\n|\A)(?:\*\*1\.|\b1\.)\s*(?:Core Principle|Concept Review|Definition)",
        re.IGNORECASE,
    )
    matches = list(pattern.finditer(raw_text))
    if len(matches) > 1:
        first_idx = matches[0].start()
        last_idx = matches[-1].start()
        return raw_text[:first_idx] + "\n" + raw_text[last_idx:].lstrip()
    return raw_text


def generate_question_coaching(row, paper):
    q_num = int(row["number"])

    if q_num <= 10:
        return (
            "**Syllabus Topic Classification:**\n"
            "General Aptitude (Verbal, Quantitative & Spatial)\n\n"
            "**Likely Misconception:**\n"
            "General Aptitude errors typically stem from misreading logical qualifiers ('all', 'some', 'not necessarily') or rushing spatial rotations.\n\n"
            "**3-Step Revision Advice:**\n"
            "1. Core Principle: Identify the exact logical constraints without assuming unstated real-world rules.\n"
            "2. Verification Shortcut: Test edge cases or counter-examples against all options.\n"
            "3. Targeted Practice: AI Study Coaching is optimized for Core Computer Science subjects (Q.11 to Q.65)."
        )

    page_number = int(paper["question_pages"][str(q_num)])
    snippet = extract_focused_question_text(paper["paper"], page_number, q_num)
    detected_subject = detect_gate_subject(snippet)

    prompt = build_cs_prompt(row, snippet, detected_subject)
    payload = json.dumps({
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "top_p": 0.85,
        },
    }).encode("utf-8")

    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=120) as response:
        data = json.loads(response.read().decode("utf-8"))
        raw_res = data["response"].strip()
        return deduplicate_revision(raw_res)