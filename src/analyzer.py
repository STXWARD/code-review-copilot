import json
import os
import time
from groq import Groq
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed

import re

load_dotenv()

# ─── API KEY ROTATION ────────────────────────────────────────────
# Load up to 3 keys. Missing / empty keys are filtered out gracefully,
# so the app works with just 1 or 2 keys set in .env.
_ALL_KEYS: list[str] = [
    k for k in [
        os.getenv("GROQ_API_KEY_1"),
        os.getenv("GROQ_API_KEY_2"),
        os.getenv("GROQ_API_KEY_3"),
    ]
    if k  # drop None and empty strings
]

if not _ALL_KEYS:
    # Fallback: support legacy single-key .env so existing setups keep working
    _legacy = os.getenv("GROQ_API_KEY")
    if _legacy:
        _ALL_KEYS = [_legacy]

_current_key_index: int = 0  # mutable global; rotated by rotate_key()


def get_groq_client() -> Groq:
    """Return a Groq client for whichever key is currently active."""
    if not _ALL_KEYS:
        raise RuntimeError("No Groq API keys found. Set GROQ_API_KEY_1 in .env")
    return Groq(api_key=_ALL_KEYS[_current_key_index])


def rotate_key() -> bool:
    """
    Advance to the next API key.
    Returns True if a new key is now active, False if all keys are exhausted.
    """
    global _current_key_index
    _current_key_index += 1
    return _current_key_index < len(_ALL_KEYS)


def call_groq_with_rotation(messages: list, max_tokens: int = 4096) -> str | None:
    """
    Call Groq chat completions with automatic key rotation on 429.

    Workflow:
        1. Try the current key.
        2. On 429 / rate-limit error → rotate_key() → retry.
        3. Repeat until a key succeeds OR all keys are exhausted.
        4. Return the raw response string, or None when every key is spent.
    """
    while True:
        try:
            client = get_groq_client()
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                temperature=0.1,
                max_tokens=max_tokens,
            )
            if not response.choices:
                raise Exception("Empty response from Groq")
            return response.choices[0].message.content.strip()

        except Exception as e:
            err_str = str(e)
            is_rate_limit = (
                '429' in err_str
                or 'rate limit' in err_str.lower()
                or 'TPD' in err_str
                or 'rate_limit_exceeded' in err_str.lower()
            )

            if is_rate_limit:
                has_next = rotate_key()
                if has_next:
                    # Silent rotation — caller never sees this exception
                    time.sleep(0.5)
                    continue
                else:
                    # All keys exhausted — surface as None so caller can handle cleanly
                    return None
            else:
                # Non-rate-limit error: re-raise so analyze_file handles it normally
                raise

# ─── TOKEN BUDGET CONTROL ────────────────────────────────────────
# 3,000 chars ≈ 750 tokens per file.
# With 15 files that's ~45k tokens per full scan — staying well
# under Groq's 100k TPD free limit and allowing ~2 full scans/day.
MAX_FILE_CHARS = 3_000


def truncate_content(content: str, max_chars: int = MAX_FILE_CHARS) -> str:
    """
    Cap file content before sending to Groq to control token spend.
    Truncates at the last newline before max_chars so we don't cut
    mid-line, then appends a comment so the model knows it's partial.
    """
    if len(content) <= max_chars:
        return content
    truncated = content[:max_chars].rsplit('\n', 1)[0]
    return truncated + f"\n# ... [file truncated at {max_chars} chars for analysis]"


SYSTEM_PROMPT = """You are an expert code reviewer with deep knowledge of software engineering best practices, security vulnerabilities, performance optimization, and clean code principles.

Your job is to analyze code and return a structured JSON array of issues found.

RULES:
- Return ONLY a valid JSON array. No markdown, no explanation, no extra text.
- If no issues found, return an empty array: []
- Each issue must follow the exact schema below
- Be specific and actionable
- Map every issue to exact line numbers

ISSUE SCHEMA:
{
  "id": "unique string like BUG001, SEC002, PERF003, SMELL004",
  "severity": "Critical" | "High" | "Medium" | "Low" | "Informational",
  "category": "bug" | "security" | "performance" | "code_smell",
  "line_start": integer,
  "line_end": integer,
  "function_name": "name of function/method or null",
  "title": "short title under 10 words",
  "description": "detailed explanation of why this is a problem",
  "affected_code": "the actual problematic code snippet",
  "suggestion": "specific fix or refactored code",
  "impact": "what happens if this is not fixed"
}

SEVERITY GUIDE:
- Critical: causes crashes, data loss, or severe security breach
- High: significant bug or security risk affecting functionality
- Medium: code smell or performance issue affecting maintainability
- Low: minor style issue or small optimization
- Informational: best practice suggestion

CATEGORIES:
- bug: logical errors, null refs, unhandled exceptions, wrong API usage
- security: injection, hardcoded secrets, weak auth, unsafe input
- performance: inefficient loops, redundant calls, memory issues
- code_smell: long functions, deep nesting, duplicates, poor naming"""


def build_prompt(file_path: str, language: str, code: str) -> str:
    return f"""Review this {language} code from file: {file_path}

Find all bugs, security vulnerabilities, performance issues, and code smells.
Return ONLY a JSON array of issues. No other text.

CODE:
````{language.lower()}
{code}
```"""


def analyze_file(file_data: dict) -> dict:
    """
    Analyze a single file using Groq API.
    Returns file_data enriched with 'issues' key.
    """
    path = file_data['path']
    language = file_data['language']
    content = file_data['content']

    result = file_data.copy()
    result['issues'] = []
    result['analysis_status'] = 'pending'

    try:
        content = truncate_content(content)
        prompt = build_prompt(path, language, content)

        raw = call_groq_with_rotation(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]
        )

        # None means every API key is exhausted
        if raw is None:
            result['analysis_status'] = 'rate_limited'
            result['error'] = 'All API keys exhausted (rate_limit)'
            result['rate_limit_wait'] = 'unknown'
            return result

        raw = raw.strip()

        # Clean markdown fences if present
        if raw.startswith("```"):
            lines = raw.split('\n')
            raw = '\n'.join(lines[1:-1])
        raw = raw.strip()

        if not raw or raw == '[]':
            result['issues'] = []
            result['analysis_status'] = 'success'
            return result

        issues = json.loads(raw)
        
        # Groq sometimes returns a dict instead of a list
        if isinstance(issues, dict):
            issues = issues.get('issues', [])
        if not isinstance(issues, list):
            issues = []
            cleaned.append({
                'id': issue.get('id', f'ISSUE{i+1:03d}'),
                'severity': issue.get('severity', 'Medium'),
                'category': issue.get('category', 'code_smell'),
                'line_start': int(issue.get('line_start', 1)),
                'line_end': int(issue.get('line_end', 1)),
                'function_name': issue.get('function_name'),
                'title': issue.get('title', 'Issue found'),
                'description': issue.get('description', ''),
                'affected_code': issue.get('affected_code', ''),
                'suggestion': issue.get('suggestion', ''),
                'impact': issue.get('impact', ''),
                'file_path': path,
                'language': language,
            })

        result['issues'] = cleaned
        result['analysis_status'] = 'success'

    except json.JSONDecodeError as e:
        result['analysis_status'] = 'parse_error'
        result['error'] = f"JSON parse error: {str(e)}"

    except Exception as e:
        err_str = str(e)

        # ── Groq 429 / daily token limit ────────────────────────────
        # Error message format: "Error code: 429 - ... Please try again in Xh Ym Zs."
        if '429' in err_str or 'rate limit' in err_str.lower() or 'TPD' in err_str:
            wait_match = re.search(
                r'try again in\s+((?:\d+h)?\s*(?:\d+m)?\s*(?:\d+s)?)',
                err_str, re.IGNORECASE
            )
            wait_time = wait_match.group(1).strip() if wait_match else 'unknown'

            result['analysis_status'] = 'rate_limited'
            result['error'] = err_str
            result['rate_limit_wait'] = wait_time
        else:
            result['analysis_status'] = 'error'
            result['error'] = err_str
            time.sleep(1)

    return result


def analyze_repository(files: list, progress_callback=None) -> list:
    """
    Analyze all files in parallel using ThreadPoolExecutor.
    Returns list of file results with issues.
    """
    results = []
    total = len(files)

    if progress_callback:
        progress_callback(f"🤖 Starting AI analysis on {total} files...")

    # Groq free tier: be careful with parallelism
    # max_workers=3 keeps us under rate limits
    with ThreadPoolExecutor(max_workers=3) as executor:
        future_to_file = {
            executor.submit(analyze_file, f): f for f in files
        }

        completed = 0
        for future in as_completed(future_to_file):
            result = future.result()
            results.append(result)
            completed += 1

            issue_count = len(result.get('issues', []))
            status = result.get('analysis_status', 'unknown')

            if progress_callback:
                if status == 'success':
                    progress_callback(
                        f"✓  ({completed}/{total}) {result['path']} "
                        f"— {issue_count} issue(s) found"
                    )
                elif status == 'rate_limited':
                    wait = result.get('rate_limit_wait', 'unknown')
                    progress_callback(
                        f"RATE_LIMITED ({completed}/{total}) {result['path']} "
                        f"— daily token limit reached. Wait: {wait}"
                    )
                else:
                    progress_callback(
                        f"⚠  ({completed}/{total}) {result['path']} "
                        f"— {status}: {result.get('error','')[:80]}"
                    )

            # Small delay to respect Groq rate limits
            time.sleep(0.5)

    results.sort(key=lambda x: len(x.get('issues', [])), reverse=True)
    return results


def get_summary_stats(results: list) -> dict:
    """Calculate summary statistics across all analyzed files."""
    total_issues = 0
    severity_counts = {
        'Critical': 0, 'High': 0,
        'Medium': 0, 'Low': 0, 'Informational': 0
    }
    category_counts = {
        'bug': 0, 'security': 0,
        'performance': 0, 'code_smell': 0
    }
    files_with_issues = 0
    all_issues = []

    for result in results:
        issues = result.get('issues', [])
        if issues:
            files_with_issues += 1
        for issue in issues:
            total_issues += 1
            sev = issue.get('severity', 'Medium')
            cat = issue.get('category', 'code_smell')
            if sev in severity_counts:
                severity_counts[sev] += 1
            if cat in category_counts:
                category_counts[cat] += 1
            all_issues.append(issue)

    risk_score = min(100, (
        severity_counts['Critical'] * 25 +
        severity_counts['High'] * 10 +
        severity_counts['Medium'] * 4 +
        severity_counts['Low'] * 1
    ))

    hotspots = sorted(
        [r for r in results if r.get('issues')],
        key=lambda x: len(x['issues']),
        reverse=True
    )[:5]

    return {
        'total_issues': total_issues,
        'files_with_issues': files_with_issues,
        'severity_counts': severity_counts,
        'category_counts': category_counts,
        'risk_score': risk_score,
        'hotspot_files': [
            {'path': h['path'], 'issue_count': len(h['issues'])}
            for h in hotspots
        ],
        'all_issues': all_issues,
    }