from collections import defaultdict


SEVERITY_WEIGHTS = {
    'Critical': 25,
    'High': 10,
    'Medium': 4,
    'Low': 1,
    'Informational': 0,
}

CATEGORY_LABELS = {
    'bug': '🐛 Bug',
    'security': '🔒 Security',
    'performance': '⚡ Performance',
    'code_smell': '🤢 Code Smell',
}

RISK_LEVELS = [
    (75, 'Critical Risk',  '#dc2626'),
    (50, 'High Risk',      '#ea580c'),
    (25, 'Medium Risk',    '#ca8a04'),
    (1,  'Low Risk',       '#16a34a'),
    (0,  'Clean',          '#15803d'),
]


def calculate_file_score(issues: list) -> int:
    """
    Calculate risk score for a single file (0–100).
    Based on weighted sum of issue severities.
    """
    raw = sum(SEVERITY_WEIGHTS.get(i.get('severity', 'Low'), 1)
              for i in issues)
    return min(100, raw)


def calculate_repo_score(all_results: list) -> int:
    """
    Calculate overall repository risk score (0–100).
    Averages file scores, weighted by issue count.
    """
    all_issues = []
    for result in all_results:
        all_issues.extend(result.get('issues', []))

    if not all_issues:
        return 0

    raw = sum(SEVERITY_WEIGHTS.get(i.get('severity', 'Low'), 1)
              for i in all_issues)
    return min(100, raw)


def get_risk_label(score: int) -> tuple:
    """
    Returns (label, color_hex) for a given score.
    Used for UI badge coloring.
    """
    for threshold, label, color in RISK_LEVELS:
        if score >= threshold:
            return label, color
    return 'Clean', '#15803d'


def build_correlation_map(all_results: list) -> list:
    """
    Correlation engine — groups related issues across files.

    Detects:
    - Same category appearing in many files (systemic problem)
    - Same severity cluster (widespread risk)
    - Repeated anti-patterns by title similarity
    """
    correlations = []

    # Group all issues by category
    by_category = defaultdict(list)
    by_severity = defaultdict(list)
    by_title_keyword = defaultdict(list)

    for result in all_results:
        for issue in result.get('issues', []):
            cat = issue.get('category', 'code_smell')
            sev = issue.get('severity', 'Medium')
            title = issue.get('title', '').lower()

            by_category[cat].append(issue)
            by_severity[sev].append(issue)

            # Extract first meaningful word from title as pattern key
            words = [w for w in title.split()
                     if len(w) > 4 and w not in
                     {'function', 'method', 'variable', 'value',
                      'error', 'issue', 'problem', 'missing'}]
            if words:
                by_title_keyword[words[0]].append(issue)

    # Systemic category patterns (3+ files affected)
    for cat, issues in by_category.items():
        affected_files = list({i['file_path'] for i in issues})
        if len(affected_files) >= 3:
            correlations.append({
                'type': 'systemic_pattern',
                'title': f'Widespread {CATEGORY_LABELS.get(cat, cat)} issues',
                'description': (
                    f'{len(issues)} {cat.replace("_", " ")} issues '
                    f'found across {len(affected_files)} files — '
                    f'suggests a systemic architectural problem.'
                ),
                'affected_files': affected_files,
                'issue_count': len(issues),
                'severity': 'High' if cat == 'security' else 'Medium',
            })

    # Critical severity cluster
    critical_issues = by_severity.get('Critical', [])
    if len(critical_issues) >= 2:
        affected_files = list({i['file_path'] for i in critical_issues})
        correlations.append({
            'type': 'severity_cluster',
            'title': f'{len(critical_issues)} Critical issues detected',
            'description': (
                f'Multiple critical issues found across '
                f'{len(affected_files)} file(s). '
                f'Immediate attention required before deployment.'
            ),
            'affected_files': affected_files,
            'issue_count': len(critical_issues),
            'severity': 'Critical',
        })

    # Repeated anti-patterns (same keyword in 3+ issue titles)
    for keyword, issues in by_title_keyword.items():
        affected_files = list({i['file_path'] for i in issues})
        if len(issues) >= 3 and len(affected_files) >= 2:
            correlations.append({
                'type': 'repeated_antipattern',
                'title': f'Repeated pattern: "{keyword}" across codebase',
                'description': (
                    f'The same type of issue ({keyword}) appears '
                    f'{len(issues)} times in {len(affected_files)} files — '
                    f'consider a codebase-wide refactor.'
                ),
                'affected_files': affected_files,
                'issue_count': len(issues),
                'severity': 'Medium',
            })

    # Sort by issue count descending
    correlations.sort(key=lambda x: x['issue_count'], reverse=True)
    return correlations


def score_all_results(all_results: list) -> dict:
    """
    Main scoring function — call this after analysis.
    Returns complete scoring data ready for the UI.
    """
    # Score each file
    scored_results = []
    for result in all_results:
        issues = result.get('issues', [])
        file_score = calculate_file_score(issues)
        risk_label, risk_color = get_risk_label(file_score)
        scored_results.append({
            **result,
            'file_score': file_score,
            'risk_label': risk_label,
            'risk_color': risk_color,
        })

    # Overall repo score
    repo_score = calculate_repo_score(all_results)
    repo_label, repo_color = get_risk_label(repo_score)

    # Severity breakdown
    severity_counts = defaultdict(int)
    category_counts = defaultdict(int)
    all_issues = []

    for result in all_results:
        for issue in result.get('issues', []):
            severity_counts[issue.get('severity', 'Medium')] += 1
            category_counts[issue.get('category', 'code_smell')] += 1
            all_issues.append(issue)

    # Correlation map
    correlations = build_correlation_map(all_results)

    # Hotspot files
    hotspots = sorted(
        [r for r in scored_results if r.get('issues')],
        key=lambda x: x['file_score'],
        reverse=True
    )[:5]

    return {
        'scored_results': scored_results,
        'repo_score': repo_score,
        'repo_label': repo_label,
        'repo_color': repo_color,
        'severity_counts': dict(severity_counts),
        'category_counts': dict(category_counts),
        'total_issues': len(all_issues),
        'all_issues': all_issues,
        'correlations': correlations,
        'hotspot_files': [
            {
                'path': h['path'],
                'score': h['file_score'],
                'label': h['risk_label'],
                'color': h['risk_color'],
                'issue_count': len(h.get('issues', [])),
            }
            for h in hotspots
        ],
    }