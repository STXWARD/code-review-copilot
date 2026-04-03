import streamlit as st
import time
from src.github_ingestion import ingest_repository
from src.analyzer import analyze_repository, get_summary_stats
from src.parser import parse_all_files, get_repo_structure_summary
from src.scoring import score_all_results
from src.report import build_full_report, filter_issues

import streamlit as st
import time
import os
os.environ["STREAMLIT_SERVER_RUN_ON_SAVE"] = "false"
# ─── PAGE CONFIG ────────────────────────────────────────────────
st.set_page_config(
    page_title="Code Review Copilot",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CUSTOM CSS ─────────────────────────────────────────────────
st.markdown("""
<style>
/* Base */
[data-testid="stAppViewContainer"] {
    background: #0d1117;
    color: #e6edf3;
}
[data-testid="stSidebar"] {
    background: #161b22;
    border-right: 1px solid #21262d;
}
[data-testid="stHeader"] { background: transparent; }

/* Typography */
h1, h2, h3 { color: #f0f6fc !important; font-weight: 700 !important; }
p, li, span { color: #e6edf3; }
label { color: #8b949e !important; font-size: 13px !important; }

/* Input */
[data-testid="stTextInput"] input {
    background: #161b22 !important;
    border: 1px solid #30363d !important;
    color: #e6edf3 !important;
    border-radius: 8px !important;
    font-size: 14px !important;
}
[data-testid="stTextInput"] input:focus {
    border-color: #388bfd !important;
    box-shadow: 0 0 0 3px rgba(56,139,253,0.1) !important;
}

/* Buttons */
[data-testid="stButton"] button {
    background: #238636 !important;
    color: white !important;
    border: 1px solid #2ea043 !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    padding: 10px 24px !important;
    transition: all 0.2s !important;
}
[data-testid="stButton"] button:hover {
    background: #2ea043 !important;
    transform: translateY(-1px) !important;
}

/* Metric cards */
[data-testid="metric-container"] {
    background: #161b22 !important;
    border: 1px solid #21262d !important;
    border-radius: 12px !important;
    padding: 16px !important;
}
[data-testid="stMetricValue"] {
    color: #f0f6fc !important;
    font-size: 28px !important;
    font-weight: 700 !important;
}
[data-testid="stMetricLabel"] {
    color: #8b949e !important;
    font-size: 12px !important;
}

/* Expanders */
[data-testid="stExpander"] {
    background: #161b22 !important;
    border: 1px solid #21262d !important;
    border-radius: 10px !important;
    margin-bottom: 8px !important;
}
[data-testid="stExpander"]:hover {
    border-color: #388bfd !important;
}

/* Selectbox */
[data-testid="stSelectbox"] > div > div {
    background: #161b22 !important;
    border: 1px solid #30363d !important;
    color: #e6edf3 !important;
    border-radius: 8px !important;
}

/* Code blocks */
code {
    background: #0d1117 !important;
    border: 1px solid #21262d !important;
    border-radius: 6px !important;
    color: #79c0ff !important;
    padding: 2px 6px !important;
}
pre {
    background: #161b22 !important;
    border: 1px solid #21262d !important;
    border-radius: 8px !important;
    padding: 16px !important;
}

/* Divider */
hr { border-color: #21262d !important; }

/* Scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #0d1117; }
::-webkit-scrollbar-thumb {
    background: #30363d;
    border-radius: 3px;
}

/* Sidebar text */
.sidebar-title {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: #8b949e;
    margin-bottom: 8px;
}

/* Custom cards */
.metric-card {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 12px;
    padding: 20px;
    text-align: center;
}
.metric-card .value {
    font-size: 32px;
    font-weight: 700;
    color: #f0f6fc;
    line-height: 1;
    margin-bottom: 6px;
}
.metric-card .label {
    font-size: 12px;
    color: #8b949e;
    text-transform: uppercase;
    letter-spacing: 1px;
}

/* Severity badges */
.badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 100px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.5px;
}
.badge-critical { background: rgba(248,81,73,0.15); color: #ff7b72; border: 1px solid rgba(248,81,73,0.4); }
.badge-high     { background: rgba(234,89,12,0.15); color: #ffa657; border: 1px solid rgba(234,89,12,0.4); }
.badge-medium   { background: rgba(210,153,34,0.15); color: #e3b341; border: 1px solid rgba(210,153,34,0.4); }
.badge-low      { background: rgba(63,185,80,0.15); color: #56d364; border: 1px solid rgba(63,185,80,0.4); }
.badge-info     { background: rgba(56,139,253,0.15); color: #79c0ff; border: 1px solid rgba(56,139,253,0.4); }

/* Issue cards */
.issue-card {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 10px;
    padding: 16px;
    margin-bottom: 10px;
    border-left: 3px solid;
}
.issue-card.critical { border-left-color: #f85149; }
.issue-card.high     { border-left-color: #ffa657; }
.issue-card.medium   { border-left-color: #e3b341; }
.issue-card.low      { border-left-color: #56d364; }
.issue-card.informational { border-left-color: #79c0ff; }

/* Risk score ring */
.score-ring {
    width: 120px;
    height: 120px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-direction: column;
    margin: 0 auto;
    font-weight: 700;
}
.score-number {
    font-size: 36px;
    font-weight: 800;
    line-height: 1;
}
.score-label {
    font-size: 11px;
    letter-spacing: 1px;
    text-transform: uppercase;
    margin-top: 4px;
}

/* Hotspot bar */
.hotspot-bar {
    background: #21262d;
    border-radius: 4px;
    height: 6px;
    overflow: hidden;
    margin-top: 4px;
}
.hotspot-fill {
    height: 100%;
    border-radius: 4px;
    background: linear-gradient(90deg, #388bfd, #bc8cff);
}

/* Section headers */
.section-header {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: #8b949e;
    border-bottom: 1px solid #21262d;
    padding-bottom: 8px;
    margin-bottom: 16px;
}

/* Correlation card */
.correlation-card {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 10px;
    padding: 14px 16px;
    margin-bottom: 8px;
}
</style>
""", unsafe_allow_html=True)


# ─── HELPERS ────────────────────────────────────────────────────
def severity_color(sev: str) -> str:
    return {
        'Critical': '#f85149',
        'High': '#ffa657',
        'Medium': '#e3b341',
        'Low': '#56d364',
        'Informational': '#79c0ff',
    }.get(sev, '#8b949e')


def severity_badge(sev: str) -> str:
    cls = {
        'Critical': 'badge-critical',
        'High': 'badge-high',
        'Medium': 'badge-medium',
        'Low': 'badge-low',
        'Informational': 'badge-info',
    }.get(sev, 'badge-info')
    emoji = {
        'Critical': '🔴',
        'High': '🟠',
        'Medium': '🟡',
        'Low': '🟢',
        'Informational': '🔵',
    }.get(sev, '⚪')
    return f'<span class="badge {cls}">{emoji} {sev}</span>'


def category_badge(cat: str) -> str:
    labels = {
        'bug': ('🐛', 'Bug'),
        'security': ('🔒', 'Security'),
        'performance': ('⚡', 'Performance'),
        'code_smell': ('🤢', 'Code Smell'),
    }
    emoji, label = labels.get(cat, ('📋', cat.title()))
    return f'<span class="badge badge-info">{emoji} {label}</span>'


def render_score_ring(score: int, label: str, color: str):
    border_color = color
    st.markdown(f"""
    <div style="text-align:center; padding: 20px 0;">
        <div style="
            width:130px; height:130px; border-radius:50%;
            border: 6px solid {border_color};
            display:flex; align-items:center;
            justify-content:center; flex-direction:column;
            margin: 0 auto; background: #161b22;
        ">
            <div style="font-size:38px; font-weight:800;
                        color:{border_color}; line-height:1;">
                {score}
            </div>
            <div style="font-size:10px; color:#8b949e;
                        letter-spacing:1px; text-transform:uppercase;
                        margin-top:4px;">
                / 100
            </div>
        </div>
        <div style="margin-top:12px; font-size:14px;
                    font-weight:600; color:{border_color};">
            {label}
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_issue_card(issue: dict):
    sev = issue.get('severity', 'Medium')
    cat = issue.get('category', 'code_smell')
    color = severity_color(sev)
    sev_lower = sev.lower()

    with st.expander(
        f"{issue.get('severity_emoji','⚪')} {issue.get('title','Issue')} "
        f"— {issue.get('file_path','').split('/')[-1]}"
        f" : {issue.get('location','')}",
        expanded=False
    ):
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            st.markdown(severity_badge(sev), unsafe_allow_html=True)
        with col2:
            st.markdown(category_badge(cat), unsafe_allow_html=True)
        with col3:
            if issue.get('function_name'):
                st.markdown(
                    f"<span style='color:#8b949e; font-size:12px;'>"
                    f"in `{issue['function_name']}`</span>",
                    unsafe_allow_html=True
                )

        st.markdown(
            f"<div style='margin:12px 0; color:#cdd9e5; "
            f"font-size:13px; line-height:1.7;'>"
            f"{issue.get('description','')}</div>",
            unsafe_allow_html=True
        )

        if issue.get('affected_code'):
            st.markdown("**Affected code:**")
            code = issue['affected_code'].replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
            st.markdown(
                f"<pre style='background:#0d1117; border:1px solid #21262d; "
                f"border-radius:6px; padding:14px; font-family:JetBrains Mono,monospace; "
                f"font-size:12px; color:#e6edf3; overflow-x:auto; "
                f"white-space:pre-wrap; word-break:break-word;'>"
                f"<code>{code}</code></pre>",
                unsafe_allow_html=True
        )

        if issue.get('suggestion'):
            st.markdown(
                f"<div style='background:#0d1117; border:1px solid "
                f"#238636; border-radius:8px; padding:12px 16px; "
                f"margin-top:8px;'>"
                f"<div style='font-size:11px; font-weight:600; "
                f"letter-spacing:1px; color:#3fb950; "
                f"text-transform:uppercase; margin-bottom:6px;'>"
                f"✅ Suggestion</div>"
                f"<div style='font-size:13px; color:#cdd9e5; "
                f"line-height:1.7;'>{issue['suggestion']}</div>"
                f"</div>",
                unsafe_allow_html=True
            )

        if issue.get('impact'):
            st.markdown(
                f"<div style='background:#0d1117; border:1px solid "
                f"#ea580c; border-radius:8px; padding:10px 14px; "
                f"margin-top:8px; font-size:12px; color:#ffa657;'>"
                f"⚠️ <b>Impact:</b> {issue['impact']}</div>",
                unsafe_allow_html=True
            )


# ─── SIDEBAR ────────────────────────────────────────────────────
def render_sidebar(report: dict):
    with st.sidebar:
        st.markdown("""
        <div style='text-align:center; padding: 16px 0 24px;'>
            <div style='font-size:28px;'>🔍</div>
            <div style='font-size:16px; font-weight:700;
                        color:#f0f6fc; margin-top:6px;'>
                Code Review Copilot
            </div>
            <div style='font-size:11px; color:#8b949e; margin-top:4px;'>
                AI-Powered Analysis
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(
            "<div class='sidebar-title'>Repository</div>",
            unsafe_allow_html=True
        )
        st.markdown(
            f"<div style='font-size:13px; color:#79c0ff; "
            f"word-break:break-all;'>"
            f"<a href='{report['repo_url']}' target='_blank' "
            f"style='color:#79c0ff;'>"
            f"📁 {report['repo_owner']}/{report['repo_name']}"
            f"</a></div>",
            unsafe_allow_html=True
        )
        st.markdown(
            f"<div style='font-size:11px; color:#8b949e; "
            f"margin-top:4px;'>Branch: {report['repo_branch']}</div>",
            unsafe_allow_html=True
        )

        st.divider()

        st.markdown(
            "<div class='sidebar-title'>Quick Stats</div>",
            unsafe_allow_html=True
        )
        stats = [
            ("📄", "Files analyzed", report['files_analyzed']),
            ("📏", "Lines of code",
             f"{report['total_lines_of_code']:,}"),
            ("⚙️", "Functions", report['total_functions']),
            ("🏛️", "Classes", report['total_classes']),
        ]
        for icon, label, value in stats:
            st.markdown(
                f"<div style='display:flex; justify-content:space-between;"
                f"align-items:center; padding:6px 0; "
                f"border-bottom:1px solid #21262d;'>"
                f"<span style='font-size:12px; color:#8b949e;'>"
                f"{icon} {label}</span>"
                f"<span style='font-size:13px; font-weight:600; "
                f"color:#f0f6fc;'>{value}</span>"
                f"</div>",
                unsafe_allow_html=True
            )

        st.divider()

        st.markdown(
            "<div class='sidebar-title'>Languages</div>",
            unsafe_allow_html=True
        )
        for lang, count in report['languages'].items():
            st.markdown(
                f"<div style='display:flex; justify-content:space-between;"
                f"align-items:center; padding:4px 0;'>"
                f"<span style='font-size:12px; color:#8b949e;'>"
                f"{lang}</span>"
                f"<span style='font-size:12px; font-weight:600; "
                f"color:#79c0ff;'>{count} file(s)</span>"
                f"</div>",
                unsafe_allow_html=True
            )

        st.divider()

        st.markdown(
            f"<div style='font-size:11px; color:#484f58; "
            f"text-align:center;'>Generated {report['generated_at']}</div>",
            unsafe_allow_html=True
        )


# ─── MAIN DASHBOARD ─────────────────────────────────────────────
def render_dashboard(report: dict):
    # Top header
    st.markdown(f"""
    <div style='margin-bottom:24px;'>
        <h1 style='font-size:26px; margin-bottom:4px;'>
            🔍 Code Review Copilot
        </h1>
        <div style='color:#8b949e; font-size:14px;'>
            AI-powered analysis of
            <span style='color:#79c0ff; font-weight:600;'>
                {report['repo_owner']}/{report['repo_name']}
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── RISK SCORE + SEVERITY BREAKDOWN ──
    col_score, col_sev, col_cat = st.columns([1, 2, 2])

    with col_score:
        st.markdown(
            "<div class='section-header'>Risk Score</div>",
            unsafe_allow_html=True
        )
        render_score_ring(
            report['repo_score'],
            report['repo_label'],
            report['repo_color']
        )

    with col_sev:
        st.markdown(
            "<div class='section-header'>Severity Breakdown</div>",
            unsafe_allow_html=True
        )
        sev_order = ['Critical', 'High', 'Medium', 'Low', 'Informational']
        for sev in sev_order:
            count = report['severity_counts'].get(sev, 0)
            color = severity_color(sev)
            pct = (count / max(report['total_issues'], 1)) * 100
            st.markdown(
                f"<div style='display:flex; align-items:center; "
                f"gap:10px; margin-bottom:8px;'>"
                f"<div style='width:80px; font-size:12px; "
                f"color:#8b949e;'>{sev}</div>"
                f"<div style='flex:1; background:#21262d; "
                f"border-radius:4px; height:8px; overflow:hidden;'>"
                f"<div style='width:{pct}%; height:100%; "
                f"background:{color}; border-radius:4px;'></div></div>"
                f"<div style='width:24px; font-size:13px; "
                f"font-weight:600; color:{color};'>{count}</div>"
                f"</div>",
                unsafe_allow_html=True
            )

    with col_cat:
        st.markdown(
            "<div class='section-header'>Category Breakdown</div>",
            unsafe_allow_html=True
        )
        cat_info = {
            'bug': ('🐛 Bugs', '#f85149'),
            'security': ('🔒 Security', '#ffa657'),
            'performance': ('⚡ Performance', '#e3b341'),
            'code_smell': ('🤢 Code Smell', '#79c0ff'),
        }
        for cat, (label, color) in cat_info.items():
            count = report['category_counts'].get(cat, 0)
            pct = (count / max(report['total_issues'], 1)) * 100
            st.markdown(
                f"<div style='display:flex; align-items:center; "
                f"gap:10px; margin-bottom:8px;'>"
                f"<div style='width:110px; font-size:12px; "
                f"color:#8b949e;'>{label}</div>"
                f"<div style='flex:1; background:#21262d; "
                f"border-radius:4px; height:8px; overflow:hidden;'>"
                f"<div style='width:{pct}%; height:100%; "
                f"background:{color}; border-radius:4px;'></div></div>"
                f"<div style='width:24px; font-size:13px; "
                f"font-weight:600; color:{color};'>{count}</div>"
                f"</div>",
                unsafe_allow_html=True
            )

    st.divider()

    # ── SUMMARY METRICS ──
    st.markdown(
        "<div class='section-header'>Summary</div>",
        unsafe_allow_html=True
    )
    m1, m2, m3, m4, m5 = st.columns(5)
    metrics = [
        (m1, "Total Issues", report['total_issues'], None),
        (m2, "Critical", report['severity_counts'].get('Critical', 0), None),
        (m3, "Security", report['category_counts'].get('security', 0), None),
        (m4, "Files Analyzed", report['files_analyzed'], None),
        (m5, "Lines of Code",
         f"{report['total_lines_of_code']:,}", None),
    ]
    for col, label, value, delta in metrics:
        with col:
            st.metric(label, value, delta)

    st.divider()
    
    # ── HOTSPOTS + CORRELATIONS ──
    col_hot, col_corr = st.columns(2)

    with col_hot:
        st.markdown(
            "<div class='section-header'>🔥 Hotspot Files</div>",
            unsafe_allow_html=True
        )
        if report['hotspot_files']:
            max_score = max(
                h['score'] for h in report['hotspot_files']
            ) or 1
            for h in report['hotspot_files']:
                pct = (h['score'] / max_score) * 100
                st.markdown(
                    f"<div style='margin-bottom:12px;'>"
                    f"<div style='display:flex; justify-content:space-between;"
                    f"align-items:center; margin-bottom:4px;'>"
                    f"<span style='font-size:12px; color:#cdd9e5; "
                    f"font-family:monospace;'>"
                    f"{h['path'].split('/')[-1]}</span>"
                    f"<span style='font-size:11px; color:{h['color']};'>"
                    f"{h['issue_count']} issues · score {h['score']}"
                    f"</span></div>"
                    f"<div class='hotspot-bar'>"
                    f"<div class='hotspot-fill' "
                    f"style='width:{pct}%;'></div></div>"
                    f"</div>",
                    unsafe_allow_html=True
                )
        else:
            st.markdown(
                "<div style='color:#8b949e; font-size:13px;'>"
                "No hotspots detected.</div>",
                unsafe_allow_html=True
            )

    with col_corr:
        st.markdown(
            "<div class='section-header'>🔗 Correlations</div>",
            unsafe_allow_html=True
        )
        if report['correlations']:
            for corr in report['correlations'][:4]:
                color = severity_color(corr.get('severity', 'Medium'))
                # Collect Issue IDs linked to this correlation's affected files
                linked_ids = [
                    i.get('id', '')
                    for i in report['all_issues']
                    if i.get('file_path', '') in corr.get('affected_files', [])
                    and i.get('id')
                ][:6]  # cap at 6 to keep card compact
                ids_html = ''
                if linked_ids:
                    ids_html = (
                        "<div style='margin-top:7px; display:flex; "
                        "flex-wrap:wrap; gap:4px;'>"
                        + ''.join(
                            f"<span style='font-size:10px; font-family:monospace; "
                            f"background:rgba(56,139,253,0.1); color:#79c0ff; "
                            f"border:1px solid rgba(56,139,253,0.3); "
                            f"border-radius:4px; padding:1px 6px;'>{id_}</span>"
                            for id_ in linked_ids
                        )
                        + ("</div>" if not (len(linked_ids) == 6) else
                           "<span style='font-size:10px;color:#484f58;'>…</span></div>")
                    )
                st.markdown(
                    f"<div class='correlation-card' "
                    f"style='border-left:3px solid {color};'>"
                    f"<div style='font-size:13px; font-weight:600; "
                    f"color:#f0f6fc; margin-bottom:4px;'>"
                    f"{corr['title']}</div>"
                    f"<div style='font-size:12px; color:#8b949e; "
                    f"line-height:1.5;'>{corr['description']}</div>"
                    f"<div style='font-size:11px; color:#484f58; "
                    f"margin-top:6px;'>"
                    f"{len(corr['affected_files'])} file(s) affected"
                    f"</div>"
                    f"{ids_html}"
                    f"</div>",
                    unsafe_allow_html=True
                )
        else:
            st.markdown(
                "<div style='color:#8b949e; font-size:13px;'>"
                "No cross-file correlations detected.</div>",
                unsafe_allow_html=True
            )

    st.divider()

    # ── FINDINGS ──
    st.markdown(
        "<div class='section-header'>📋 Findings</div>",
        unsafe_allow_html=True
    )

    # Filters
    f1, f2, f3, f4, f5 = st.columns([2, 1, 1, 1, 1])
    with f1:
        file_options = ['All'] + list({
            i.get('file_path', '') for i in report['all_issues']
        })
        selected_file = st.selectbox(
            "File", file_options,
            format_func=lambda x: x.split('/')[-1] if x != 'All' else 'All files'
        )
    with f2:
        selected_sev = st.selectbox(
            "Severity",
            ['All', 'Critical', 'High', 'Medium', 'Low', 'Informational']
        )
    with f3:
        selected_cat = st.selectbox(
            "Category",
            ['All', 'bug', 'security', 'performance', 'code_smell'],
            format_func=lambda x: x.replace('_', ' ').title()
        )
    with f4:
        # Component filter — all unique function names across issues
        fn_options = ['All'] + sorted(list({
            i.get('function_name', '')
            for i in report['all_issues']
            if i.get('function_name')
        }))
        selected_fn = st.selectbox(
            "Component",
            fn_options,
            format_func=lambda x: x if x != 'All' else 'All components'
        )
    with f5:
        sort_by = st.selectbox(
            "Sort by",
            ['Severity', 'File', 'Category']
        )

    # Apply filters
    filtered = filter_issues(
        report['all_issues'],
        severity=selected_sev,
        category=selected_cat,
        file_path=selected_file,
    )
    # Component filter applied client-side (function_name not in filter_issues signature)
    if selected_fn != 'All':
        filtered = [i for i in filtered if i.get('function_name') == selected_fn]

    # Sort
    sev_order = {
        'Critical': 0, 'High': 1,
        'Medium': 2, 'Low': 3, 'Informational': 4
    }
    if sort_by == 'Severity':
        filtered.sort(key=lambda x: sev_order.get(x.get('severity', 'Low'), 5))
    elif sort_by == 'File':
        filtered.sort(key=lambda x: x.get('file_path', ''))
    elif sort_by == 'Category':
        filtered.sort(key=lambda x: x.get('category', ''))

    st.markdown(
        f"<div style='font-size:12px; color:#8b949e; "
        f"margin-bottom:12px;'>"
        f"Showing {len(filtered)} of {report['total_issues']} issues</div>",
        unsafe_allow_html=True
    )

    if filtered:
        for issue in filtered:
            render_issue_card(issue)
    else:
        st.markdown(
            "<div style='text-align:center; padding:40px; "
            "color:#8b949e;'>✅ No issues match your filters.</div>",
            unsafe_allow_html=True
        )


# ─── LANDING PAGE ────────────────────────────────────────────────
def render_landing():
    st.markdown("""
    <div style='text-align:center; padding: 60px 20px 40px;'>
        <div style='font-size:56px; margin-bottom:16px;'>🔍</div>
        <h1 style='font-size:36px; font-weight:800;
                   background: linear-gradient(135deg, #58a6ff, #bc8cff);
                   -webkit-background-clip: text;
                   -webkit-text-fill-color: transparent;
                   margin-bottom:12px;'>
            Code Review Copilot
        </h1>
        <p style='font-size:16px; color:#8b949e; max-width:500px;
                  margin:0 auto 40px; line-height:1.7;'>
            AI-powered code review for any GitHub repository.
            Detect bugs, security vulnerabilities, performance issues,
            and code smells in seconds.
        </p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        github_url = st.text_input(
            "GitHub Repository URL",
            placeholder="https://github.com/owner/repository",
            label_visibility="collapsed",
        )

        col_btn, col_opt = st.columns([1, 1])
        with col_btn:
            analyze = st.button("🔍 Analyze Repository", use_container_width=True)
        with col_opt:
            github_token = st.text_input(
                "GitHub Token (optional)",
                type="password",
                placeholder="ghp_... (for private repos)",
                label_visibility="collapsed",
            )

    # Feature pills
    st.markdown("""
    <div style='display:flex; justify-content:center; gap:10px;
                flex-wrap:wrap; margin-top:32px;'>
        <span class='badge badge-critical'>🐛 Bug Detection</span>
        <span class='badge badge-high'>🔒 Security Analysis</span>
        <span class='badge badge-medium'>⚡ Performance Review</span>
        <span class='badge badge-low'>🤢 Code Smell Detection</span>
        <span class='badge badge-info'>🔗 Correlation Engine</span>
    </div>
    """, unsafe_allow_html=True)

    return github_url, analyze, github_token


# ─── ANALYSIS PIPELINE ──────────────────────────────────────────
def run_analysis(github_url: str, token: str = None):
    log_messages = []

    def log(msg):
        log_messages.append(msg)
        status_text.markdown(
            f"<div style='font-size:13px; color:#8b949e; "
            f"font-family:monospace;'>{msg}</div>",
            unsafe_allow_html=True
        )

    progress = st.progress(0)
    status_text = st.empty()

    try:
        # Step 1 — Ingest
        log("📡 Connecting to GitHub...")
        repo_data = ingest_repository(github_url, token, log)
        progress.progress(20)

        if not repo_data['files']:
            st.error("❌ No analyzable files found in this repository.")
            return None

        # Step 2 — Parse structure
        log("🔬 Parsing code structure...")
        parsed_files = parse_all_files(repo_data['files'])
        structure_summary = get_repo_structure_summary(parsed_files)
        progress.progress(35)

        # Step 3 — AI Analysis
        log(f"🤖 Running AI analysis on {len(parsed_files)} files...")
        analysis_results = analyze_repository(parsed_files, log)
        progress.progress(75)

        # Step 4 — Score
        log("📊 Calculating scores and correlations...")
        scoring_data = score_all_results(analysis_results)
        progress.progress(90)

        # Step 5 — Report
        log("📄 Building report...")
        report = build_full_report(scoring_data, repo_data, structure_summary)
        progress.progress(100)

        log("✅ Analysis complete!")
        time.sleep(0.5)
        progress.empty()
        status_text.empty()
        st.session_state.report = report
        return report

    except ValueError as e:
        st.error(f"❌ {str(e)}")
        progress.empty()
        status_text.empty()
        return None

    except Exception as e:
        st.error(f"❌ Unexpected error: {str(e)}")
        progress.empty()
        status_text.empty()
        return None


# ─── MAIN ───────────────────────────────────────────────────────
def main():
    if 'report' not in st.session_state:
        st.session_state.report = None

    if st.session_state.report is None:
        github_url, analyze, token = render_landing()

        if analyze and github_url:
            st.session_state.analyzing = True
            st.session_state.github_url = github_url
            st.session_state.token = token
            st.rerun()

    if st.session_state.get('analyzing') and not st.session_state.report:
        report = run_analysis(
            st.session_state.github_url,
            st.session_state.token or None
        )
        if report:
            st.session_state.report = report
            st.session_state.analyzing = False
            st.rerun()
        elif analyze and not github_url:
            st.warning("⚠️ Please enter a GitHub repository URL.")

    else:
        report = st.session_state.report
        render_sidebar(report)
        render_dashboard(report)

        with st.sidebar:
            st.divider()
            if st.button("🔄 Analyze New Repo", use_container_width=True):
                st.session_state.report = None
                st.rerun()


if __name__ == "__main__":
    main()