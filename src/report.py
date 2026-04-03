from datetime import datetime


def format_issue_for_display(issue: dict) -> dict:
    """
    Clean and format a single issue for UI display.
    Adds emoji indicators and display-friendly labels.
    """
    severity_emoji = {
        'Critical': '🔴',
        'High': '🟠',
        'Medium': '🟡',
        'Low': '🟢',
        'Informational': '🔵',
    }

    category_emoji = {
        'bug': '🐛',
        'security': '🔒',
        'performance': '⚡',
        'code_smell': '🤢',
    }

    sev = issue.get('severity', 'Medium')
    cat = issue.get('category', 'code_smell')

    return {
        **issue,
        'severity_emoji': severity_emoji.get(sev, '⚪'),
        'category_emoji': category_emoji.get(cat, '📋'),
        'severity_display': f"{severity_emoji.get(sev, '')} {sev}",
        'category_display': f"{category_emoji.get(cat, '')} {cat.replace('_', ' ').title()}",
        'location': (
            f"Line {issue.get('line_start', '?')}"
            if issue.get('line_start') == issue.get('line_end')
            else f"Lines {issue.get('line_start', '?')}–{issue.get('line_end', '?')}"
        ),
    }


def build_file_report(result: dict) -> dict:
    """
    Build a complete report for a single file.
    """
    issues = result.get('issues', [])
    formatted_issues = [format_issue_for_display(i) for i in issues]

    # Group issues by category for this file
    by_category = {}
    for issue in formatted_issues:
        cat = issue.get('category', 'code_smell')
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(issue)

    # Group by severity
    by_severity = {}
    for issue in formatted_issues:
        sev = issue.get('severity', 'Medium')
        if sev not in by_severity:
            by_severity[sev] = []
        by_severity[sev].append(issue)

    return {
        'path': result.get('path', ''),
        'language': result.get('language', 'Unknown'),
        'size_lines': result.get('size_lines', 0),
        'total_functions': result.get('total_functions', 0),
        'total_classes': result.get('total_classes', 0),
        'complexity_score': result.get('complexity_score', 0),
        'file_score': result.get('file_score', 0),
        'risk_label': result.get('risk_label', 'Clean'),
        'risk_color': result.get('risk_color', '#15803d'),
        'total_issues': len(issues),
        'issues': formatted_issues,
        'by_category': by_category,
        'by_severity': by_severity,
        'analysis_status': result.get('analysis_status', 'unknown'),
    }


def build_full_report(scoring_data: dict, repo_info: dict,
                      structure_summary: dict) -> dict:
    """
    Build the complete repository report.
    This is the final output object passed to the UI.
    """
    scored_results = scoring_data.get('scored_results', [])

    file_reports = [build_file_report(r) for r in scored_results]

    # Total lines of code
    total_lines = sum(
        r.get('size_lines', 0) for r in scored_results
    )

    return {
        # Metadata
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'repo_owner': repo_info.get('owner', ''),
        'repo_name': repo_info.get('repo', ''),
        'repo_branch': repo_info.get('branch', 'main'),
        'repo_url': f"https://github.com/{repo_info.get('owner', '')}/{repo_info.get('repo', '')}",

        # Summary stats
        'total_files_in_repo': repo_info.get('total_files_in_repo', 0),
        'files_analyzed': repo_info.get('files_analyzed', 0),
        'total_lines_of_code': total_lines,
        'languages': repo_info.get('languages', {}),

        # Structure
        'total_functions': structure_summary.get('total_functions', 0),
        'total_classes': structure_summary.get('total_classes', 0),
        'total_complexity': structure_summary.get('total_complexity', 0),

        # Risk scoring
        'repo_score': scoring_data.get('repo_score', 0),
        'repo_label': scoring_data.get('repo_label', 'Clean'),
        'repo_color': scoring_data.get('repo_color', '#15803d'),

        # Issues
        'total_issues': scoring_data.get('total_issues', 0),
        'severity_counts': scoring_data.get('severity_counts', {}),
        'category_counts': scoring_data.get('category_counts', {}),
        'all_issues': [
            format_issue_for_display(i)
            for i in scoring_data.get('all_issues', [])
        ],

        # Correlations
        'correlations': scoring_data.get('correlations', []),

        # Hotspots
        'hotspot_files': scoring_data.get('hotspot_files', []),

        # Per-file reports
        'file_reports': file_reports,
    }


def filter_issues(all_issues: list, severity: str = 'All',
                  category: str = 'All', file_path: str = 'All') -> list:
    """
    Filter issues by severity, category, and file.
    Used by UI filter controls.
    """
    filtered = all_issues

    if severity != 'All':
        filtered = [i for i in filtered
                    if i.get('severity') == severity]

    if category != 'All':
        filtered = [i for i in filtered
                    if i.get('category') == category]

    if file_path != 'All':
        filtered = [i for i in filtered
                    if i.get('file_path') == file_path]

    return filtered


def get_issue_counts_by_file(file_reports: list) -> list:
    """
    Returns sorted list of files by issue count.
    Used to populate file filter dropdown in UI.
    """
    return sorted(
        [
            {
                'path': r['path'],
                'count': r['total_issues'],
                'score': r['file_score'],
            }
            for r in file_reports
            if r['total_issues'] > 0
        ],
        key=lambda x: x['score'],
        reverse=True
    )
