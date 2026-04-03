import streamlit as st
import time
from src.github_ingestion import ingest_repository
from src.analyzer import analyze_repository, get_summary_stats
from src.parser import parse_all_files, get_repo_structure_summary
from src.scoring import score_all_results
from src.report import build_full_report, filter_issues

# ─── PAGE CONFIG ────────────────────────────────────────────────
st.set_page_config(
    page_title="Code Review Copilot",
    page_icon="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>⬡</text></svg>",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── FONTS + GLOBAL CSS ─────────────────────────────────────────
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">

<style>
/* ── RESET & BASE ── */
html, body, [data-testid="stAppViewContainer"] {
    background: #0A0A0C !important;
    color: #F0F0F5 !important;
    font-family: 'Inter', sans-serif !important;
}

/* Grid-dot background on main area */
[data-testid="stAppViewContainer"] > .main {
    background-image: radial-gradient(circle, #21212B 1px, transparent 1px) !important;
    background-size: 28px 28px !important;
    background-position: 0 0 !important;
}

[data-testid="stHeader"] { background: transparent !important; }

/* ── SCROLLBAR ── */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: #0A0A0C; }
::-webkit-scrollbar-thumb { background: #21212B; border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: #3B82F6; }

/* ── SIDEBAR ── */
[data-testid="stSidebar"] {
    background: #111115 !important;
    border-right: 1px solid #21212B !important;
}
[data-testid="stSidebar"] > div { padding-top: 0 !important; }

/* ── TYPOGRAPHY ── */
h1, h2, h3, h4, h5, h6 {
    font-family: 'Space Grotesk', sans-serif !important;
    color: #F0F0F5 !important;
    letter-spacing: -0.02em !important;
}

/* ── INPUT ── */
[data-testid="stTextInput"] > div > div > input {
    background: #111115 !important;
    border: 1px solid #21212B !important;
    color: #F0F0F5 !important;
    border-radius: 6px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 14px !important;
    padding: 10px 14px !important;
    transition: border-color 0.15s, box-shadow 0.15s !important;
}
[data-testid="stTextInput"] > div > div > input:focus {
    border-color: #3B82F6 !important;
    box-shadow: 0 0 0 2px rgba(59,130,246,0.25) !important;
    outline: none !important;
}
[data-testid="stTextInput"] > div > div > input::placeholder {
    color: #7070A0 !important;
}

/* ── BUTTONS ── */
[data-testid="stButton"] > button {
    background: #3B82F6 !important;
    color: #fff !important;
    border: 1px solid #3B82F6 !important;
    border-radius: 6px !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    letter-spacing: 0.04em !important;
    text-transform: uppercase !important;
    padding: 9px 20px !important;
    transition: background 0.15s, transform 0.1s, box-shadow 0.15s !important;
}
[data-testid="stButton"] > button:hover {
    background: #2563EB !important;
    border-color: #2563EB !important;
    box-shadow: 0 0 0 3px rgba(59,130,246,0.2) !important;
    transform: translateY(-1px) !important;
}
[data-testid="stButton"] > button:active {
    transform: translateY(0) !important;
}

/* ── METRICS ── */
[data-testid="metric-container"] {
    background: #111115 !important;
    border: 1px solid #21212B !important;
    border-radius: 6px !important;
    padding: 16px !important;
    transition: border-color 0.15s !important;
}
[data-testid="metric-container"]:hover {
    border-color: #3B82F6 !important;
}
[data-testid="stMetricValue"] {
    font-family: 'JetBrains Mono', monospace !important;
    color: #F0F0F5 !important;
    font-size: 26px !important;
    font-weight: 700 !important;
}
[data-testid="stMetricLabel"] {
    font-family: 'Inter', sans-serif !important;
    color: #7070A0 !important;
    font-size: 11px !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
}

/* ── EXPANDERS ── */
[data-testid="stExpander"] {
    background: #111115 !important;
    border: 1px solid #21212B !important;
    border-radius: 6px !important;
    margin-bottom: 6px !important;
    overflow: hidden !important;
}
[data-testid="stExpander"]:hover {
    border-color: #3B82F6 !important;
}
[data-testid="stExpander"] summary {
    font-family: 'Inter', sans-serif !important;
    font-size: 13px !important;
    color: #F0F0F5 !important;
    padding: 12px 16px !important;
}

/* ── SELECTBOX ── */
[data-testid="stSelectbox"] > div > div {
    background: #111115 !important;
    border: 1px solid #21212B !important;
    color: #F0F0F5 !important;
    border-radius: 6px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 13px !important;
}

/* ── CODE ── */
code {
    background: #111115 !important;
    border: 1px solid #21212B !important;
    border-radius: 4px !important;
    color: #93C5FD !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 12px !important;
    padding: 2px 6px !important;
}
pre {
    background: #111115 !important;
    border: 1px solid #21212B !important;
    border-radius: 6px !important;
    padding: 16px !important;
    font-family: 'JetBrains Mono', monospace !important;
}

/* ── DIVIDER ── */
hr { border-color: #21212B !important; margin: 20px 0 !important; }

/* ── PROGRESS BAR ── */
[data-testid="stProgress"] > div > div {
    background: #3B82F6 !important;
    border-radius: 4px !important;
}
[data-testid="stProgress"] > div {
    background: #21212B !important;
    border-radius: 4px !important;
}

/* ── ALERTS ── */
[data-testid="stAlert"] {
    background: #111115 !important;
    border-radius: 6px !important;
    border: 1px solid #21212B !important;
    font-family: 'Inter', sans-serif !important;
}

/* ── CUSTOM COMPONENT STYLES ── */

/* Section header */
.rc-section-header {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #7070A0;
    border-bottom: 1px solid #21212B;
    padding-bottom: 10px;
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 8px;
}

/* Severity badge */
.rc-badge {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 3px 9px;
    border-radius: 4px;
    font-family: 'Space Grotesk', sans-serif;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.04em;
}
.rc-badge-critical { background: rgba(239,68,68,0.12); color: #EF4444; border: 1px solid rgba(239,68,68,0.35); }
.rc-badge-high     { background: rgba(249,115,22,0.12); color: #F97316; border: 1px solid rgba(249,115,22,0.35); }
.rc-badge-medium   { background: rgba(234,179,8,0.12);  color: #EAB308; border: 1px solid rgba(234,179,8,0.35);  }
.rc-badge-low      { background: rgba(59,130,246,0.12); color: #3B82F6; border: 1px solid rgba(59,130,246,0.35); }
.rc-badge-info     { background: rgba(59,130,246,0.08); color: #7070A0; border: 1px solid rgba(59,130,246,0.2);  }
.rc-badge-cat      { background: rgba(112,112,160,0.1); color: #A0A0C0; border: 1px solid rgba(112,112,160,0.25); }

/* Issue card */
.rc-issue-card {
    background: #111115;
    border: 1px solid #21212B;
    border-radius: 6px;
    padding: 14px 16px;
    margin-bottom: 8px;
    border-left: 3px solid;
    animation: fadeUp 0.3s ease both;
}
.rc-issue-card.critical  { border-left-color: #EF4444; }
.rc-issue-card.high      { border-left-color: #F97316; }
.rc-issue-card.medium    { border-left-color: #EAB308; }
.rc-issue-card.low       { border-left-color: #3B82F6; }
.rc-issue-card.informational { border-left-color: #7070A0; }

/* Hotspot bar */
.rc-hotspot-row { margin-bottom: 14px; }
.rc-hotspot-meta {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 5px;
}
.rc-hotspot-name {
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    color: #C0C0E0;
}
.rc-hotspot-score {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: #7070A0;
}
.rc-hotspot-track {
    background: #18181F;
    border-radius: 3px;
    height: 5px;
    overflow: hidden;
    border: 1px solid #21212B;
}
.rc-hotspot-fill {
    height: 100%;
    border-radius: 3px;
    transition: width 0.6s ease;
}

/* Correlation card */
.rc-corr-card {
    background: #111115;
    border: 1px solid #21212B;
    border-radius: 6px;
    padding: 12px 14px;
    margin-bottom: 8px;
    border-left: 3px solid;
}
.rc-corr-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 13px;
    font-weight: 600;
    color: #F0F0F5;
    margin-bottom: 5px;
}
.rc-corr-desc {
    font-family: 'Inter', sans-serif;
    font-size: 12px;
    color: #7070A0;
    line-height: 1.6;
}
.rc-corr-meta {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: #3B3B55;
    margin-top: 7px;
}

/* Sidebar stat card */
.rc-stat-card {
    background: #18181F;
    border: 1px solid #21212B;
    border-radius: 6px;
    padding: 10px 12px;
    margin-bottom: 6px;
}
.rc-stat-label {
    font-family: 'Inter', sans-serif;
    font-size: 10px;
    font-weight: 500;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #7070A0;
    margin-bottom: 3px;
}
.rc-stat-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 18px;
    font-weight: 700;
    color: #F0F0F5;
    line-height: 1.2;
}

/* Suggestion block */
.rc-suggestion {
    background: #0E1117;
    border: 1px solid rgba(16,185,129,0.3);
    border-radius: 6px;
    padding: 11px 14px;
    margin-top: 10px;
}
.rc-suggestion-label {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #10B981;
    margin-bottom: 6px;
    display: flex;
    align-items: center;
    gap: 6px;
}
.rc-suggestion-text {
    font-family: 'Inter', sans-serif;
    font-size: 13px;
    color: #C0C0E0;
    line-height: 1.7;
}

/* Impact block */
.rc-impact {
    background: #0E1117;
    border: 1px solid rgba(249,115,22,0.25);
    border-radius: 6px;
    padding: 9px 13px;
    margin-top: 8px;
    font-family: 'Inter', sans-serif;
    font-size: 12px;
    color: #F97316;
    line-height: 1.5;
}

/* Fade-up animation */
@keyframes fadeUp {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
}

/* Feature pills on landing */
.rc-pill-row {
    display: flex;
    justify-content: center;
    gap: 8px;
    flex-wrap: wrap;
    margin-top: 28px;
}

/* Header bar */
.rc-app-header {
    background: #111115;
    border-bottom: 1px solid #21212B;
    padding: 14px 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin: -1rem -1rem 24px -1rem;
    background-image: radial-gradient(circle, #1a1a24 1px, transparent 1px);
    background-size: 20px 20px;
}
.rc-app-header-name {
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 700;
    font-size: 16px;
    color: #F0F0F5;
    letter-spacing: -0.02em;
    display: flex;
    align-items: center;
    gap: 10px;
}
.rc-app-header-tag {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    color: #7070A0;
    background: #18181F;
    border: 1px solid #21212B;
    border-radius: 4px;
    padding: 2px 7px;
}

/* Sidebar header */
.rc-sidebar-brand {
    padding: 20px 16px 16px;
    border-bottom: 1px solid #21212B;
    margin-bottom: 16px;
}
.rc-sidebar-brand-name {
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 700;
    font-size: 14px;
    color: #F0F0F5;
    letter-spacing: -0.01em;
    margin-top: 8px;
}
.rc-sidebar-brand-sub {
    font-family: 'Inter', sans-serif;
    font-size: 11px;
    color: #7070A0;
    margin-top: 2px;
}
.rc-sidebar-section-label {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #3B3B55;
    margin: 16px 0 8px;
    padding: 0 4px;
}
</style>
""", unsafe_allow_html=True)


# ─── LUCIDE ICONS ────────────────────────────────────────────────
def icon(name: str, size: int = 16, color: str = "currentColor") -> str:
    """Returns inline SVG for a Lucide icon by name."""
    paths = {
        "bug": '<path d="M8 2v2"/><path d="M16 2v2"/><path d="M9 8H4l-2 2 2 2h5"/><path d="M15 8h5l2 2-2 2h-5"/><rect width="10" height="12" x="7" y="6" rx="5"/><path d="M12 18v4"/><path d="M12 6V2"/><path d="M7 16H2"/><path d="M22 16h-5"/>',
        "shield-alert": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="M12 8v4"/><path d="M12 16h.01"/>',
        "zap": '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
        "code-2": '<path d="m18 16 4-4-4-4"/><path d="m6 8-4 4 4 4"/><path d="m14.5 4-5 16"/>',
        "flame": '<path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"/>',
        "gauge": '<path d="m12 14 4-4"/><path d="M3.34 19a10 10 0 1 1 17.32 0"/>',
        "git-merge": '<circle cx="18" cy="18" r="3"/><circle cx="6" cy="6" r="3"/><path d="M6 21V9a9 9 0 0 0 9 9"/>',
        "lightbulb": '<path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5"/><path d="M9 18h6"/><path d="M10 22h4"/>',
        "file-code-2": '<path d="M4 22h14a2 2 0 0 0 2-2V7l-5-5H6a2 2 0 0 0-2 2v4"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="m5 12-3 3 3 3"/><path d="m11 18 3-3-3-3"/>',
        "scan-search": '<path d="M3 7V5a2 2 0 0 1 2-2h2"/><path d="M17 3h2a2 2 0 0 1 2 2v2"/><path d="M21 17v2a2 2 0 0 1-2 2h-2"/><path d="M7 21H5a2 2 0 0 1-2-2v-2"/><circle cx="12" cy="12" r="3"/><path d="m16 16-1.9-1.9"/>',
        "triangle-alert": '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
        "circle-check": '<circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>',
        "folder": '<path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.93a2 2 0 0 1-1.66-.9l-.82-1.2A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13c0 1.1.9 2 2 2Z"/>',
        "refresh-cw": '<path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M8 16H3v5"/>',
        "layers": '<path d="m12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z"/><path d="m22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 17.65"/><path d="m22 12.65-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65"/>',
        "terminal": '<polyline points="4 17 10 11 4 5"/><line x1="12" x2="20" y1="19" y2="19"/>',
    }
    p = paths.get(name, '<circle cx="12" cy="12" r="10"/>')
    return (
        f'<span style="display:inline-flex;align-items:center;vertical-align:middle;">'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" '
        f'stroke-linecap="round" stroke-linejoin="round">{p}</svg></span>'
    )


# ─── HELPERS ────────────────────────────────────────────────────
def severity_color(sev: str) -> str:
    return {
        'Critical':      '#EF4444',
        'High':          '#F97316',
        'Medium':        '#EAB308',
        'Low':           '#3B82F6',
        'Informational': '#7070A0',
    }.get(sev, '#7070A0')


def severity_badge(sev: str) -> str:
    cls = {
        'Critical':      'rc-badge-critical',
        'High':          'rc-badge-high',
        'Medium':        'rc-badge-medium',
        'Low':           'rc-badge-low',
        'Informational': 'rc-badge-info',
    }.get(sev, 'rc-badge-info')
    ico = {
        'Critical':      icon('triangle-alert', 12, '#EF4444'),
        'High':          icon('triangle-alert', 12, '#F97316'),
        'Medium':        icon('triangle-alert', 12, '#EAB308'),
        'Low':           icon('triangle-alert', 12, '#3B82F6'),
        'Informational': icon('circle-check',   12, '#7070A0'),
    }.get(sev, '')
    return f'<span class="rc-badge {cls}">{ico} {sev}</span>'


def category_badge(cat: str) -> str:
    mapping = {
        'bug':         ('bug',          '#EF4444', 'Bug'),
        'security':    ('shield-alert', '#F97316', 'Security'),
        'performance': ('zap',          '#EAB308', 'Performance'),
        'code_smell':  ('code-2',       '#7070A0', 'Code Smell'),
    }
    ico_name, color, label = mapping.get(cat, ('layers', '#7070A0', cat.title()))
    return (
        f'<span class="rc-badge rc-badge-cat">'
        f'{icon(ico_name, 12, color)} {label}</span>'
    )


def render_score_ring(score: int, label: str, color: str):
    """SVG donut chart risk score ring."""
    r = 52
    cx = cy = 70
    circumference = 2 * 3.14159 * r
    filled = circumference * (score / 100)
    gap    = circumference - filled

    ring_color = color  # already computed upstream
    st.markdown(f"""
    <div style="text-align:center; padding:16px 0 20px;">
        <svg width="140" height="140" viewBox="0 0 140 140"
             style="display:block; margin:0 auto; overflow:visible;">
            <!-- track -->
            <circle cx="{cx}" cy="{cy}" r="{r}"
                fill="none" stroke="#18181F" stroke-width="10"/>
            <!-- fill -->
            <circle cx="{cx}" cy="{cy}" r="{r}"
                fill="none"
                stroke="{ring_color}"
                stroke-width="10"
                stroke-linecap="round"
                stroke-dasharray="{filled:.1f} {gap:.1f}"
                stroke-dashoffset="{circumference * 0.25:.1f}"
                style="transition: stroke-dasharray 0.8s ease;"/>
            <!-- score number -->
            <text x="{cx}" y="{cy - 6}"
                font-family="JetBrains Mono, monospace"
                font-size="32" font-weight="700"
                fill="{ring_color}"
                text-anchor="middle" dominant-baseline="middle">{score}</text>
            <!-- /100 -->
            <text x="{cx}" y="{cy + 18}"
                font-family="Inter, sans-serif"
                font-size="10" fill="#7070A0"
                text-anchor="middle">/100</text>
        </svg>
        <div style="margin-top:8px; font-family:'Space Grotesk',sans-serif;
                    font-size:13px; font-weight:600; color:{ring_color};">
            {icon('gauge', 14, ring_color)} {label}
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_issue_card(issue: dict, idx: int = 0):
    sev = issue.get('severity', 'Medium')
    cat = issue.get('category', 'code_smell')
    color = severity_color(sev)
    sev_lower = sev.lower()
    delay = f"{idx * 0.04:.2f}s"

    title     = issue.get('title', 'Issue')
    file_name = issue.get('file_path', '').split('/')[-1]
    location  = issue.get('location', '')
    desc      = issue.get('description', '')
    fn_name   = issue.get('function_name', '')
    affected  = issue.get('affected_code', '')
    suggestion = issue.get('suggestion', '')
    impact    = issue.get('impact', '')
    lang      = issue.get('language', 'python').lower()

    expander_label = (
        f"{title}  ·  "
        f"{file_name}"
        + (f"  :  {location}" if location else "")
    )

    with st.expander(expander_label, expanded=False):
        # badges row
        badge_html = (
            f"<div style='display:flex; gap:8px; align-items:center; "
            f"flex-wrap:wrap; margin-bottom:12px;'>"
            f"{severity_badge(sev)}"
            f"{category_badge(cat)}"
        )
        if fn_name:
            badge_html += (
                f"<span style='font-family:JetBrains Mono,monospace; "
                f"font-size:11px; color:#7070A0;'>"
                f"{icon('terminal', 11, '#7070A0')} {fn_name}</span>"
            )
        badge_html += "</div>"
        st.markdown(badge_html, unsafe_allow_html=True)

        # file path
        st.markdown(
            f"<div style='font-family:JetBrains Mono,monospace; font-size:11px; "
            f"color:#3B3B55; margin-bottom:10px;'>"
            f"{icon('file-code-2', 11, '#3B3B55')} "
            f"{issue.get('file_path','')}"
            + (f"  ·  line {location}" if location else "")
            + "</div>",
            unsafe_allow_html=True
        )

        # description
        st.markdown(
            f"<div style='font-family:Inter,sans-serif; font-size:13px; "
            f"color:#C0C0E0; line-height:1.75; margin-bottom:10px;'>{desc}</div>",
            unsafe_allow_html=True
        )

        if affected:
            st.markdown(
                f"<div style='font-family:Space Grotesk,sans-serif; font-size:10px; "
                f"font-weight:600; letter-spacing:0.1em; text-transform:uppercase; "
                f"color:#7070A0; margin-bottom:6px;'>Affected Code</div>",
                unsafe_allow_html=True
            )
            st.code(affected, language=lang or 'python')

        if suggestion:
            st.markdown(
                f"<div class='rc-suggestion'>"
                f"<div class='rc-suggestion-label'>"
                f"{icon('lightbulb', 12, '#10B981')} Suggestion</div>"
                f"<div class='rc-suggestion-text'>{suggestion}</div>"
                f"</div>",
                unsafe_allow_html=True
            )

        if impact:
            st.markdown(
                f"<div class='rc-impact'>"
                f"{icon('triangle-alert', 12, '#F97316')} "
                f"<strong style='color:#F97316;'>Impact:</strong> {impact}"
                f"</div>",
                unsafe_allow_html=True
            )


# ─── SIDEBAR ────────────────────────────────────────────────────
def render_sidebar(report: dict):
    with st.sidebar:
        st.markdown(f"""
        <div class="rc-sidebar-brand">
            {icon('scan-search', 22, '#3B82F6')}
            <div class="rc-sidebar-brand-name">Code Review Copilot</div>
            <div class="rc-sidebar-brand-sub">AI-Powered Analysis</div>
        </div>
        """, unsafe_allow_html=True)

        # Repo
        st.markdown(
            f"<div class='rc-sidebar-section-label'>Repository</div>",
            unsafe_allow_html=True
        )
        st.markdown(
            f"<div style='font-family:JetBrains Mono,monospace; font-size:12px; "
            f"color:#3B82F6; word-break:break-all; padding: 0 4px 12px;'>"
            f"{icon('folder', 12, '#3B82F6')} "
            f"<a href='{report['repo_url']}' target='_blank' "
            f"style='color:#3B82F6; text-decoration:none;'>"
            f"{report['repo_owner']}/{report['repo_name']}"
            f"</a></div>"
            f"<div style='font-family:Inter,sans-serif; font-size:11px; "
            f"color:#7070A0; padding: 0 4px; margin-top:-8px; "
            f"margin-bottom:12px;'>branch: {report['repo_branch']}</div>",
            unsafe_allow_html=True
        )

        st.markdown(
            "<div style='border-top:1px solid #21212B; margin:4px 0 12px;'></div>",
            unsafe_allow_html=True
        )

        # Quick stats
        st.markdown(
            "<div class='rc-sidebar-section-label'>Quick Stats</div>",
            unsafe_allow_html=True
        )
        stats = [
            ("Files Analyzed",   report['files_analyzed']),
            ("Lines of Code",    f"{report['total_lines_of_code']:,}"),
            ("Functions",        report['total_functions']),
            ("Classes",          report['total_classes']),
        ]
        for label, value in stats:
            st.markdown(
                f"<div class='rc-stat-card'>"
                f"<div class='rc-stat-label'>{label}</div>"
                f"<div class='rc-stat-value'>{value}</div>"
                f"</div>",
                unsafe_allow_html=True
            )

        st.markdown(
            "<div style='border-top:1px solid #21212B; margin:12px 0;'></div>",
            unsafe_allow_html=True
        )

        # Languages
        st.markdown(
            "<div class='rc-sidebar-section-label'>Languages</div>",
            unsafe_allow_html=True
        )
        for lang, count in report['languages'].items():
            st.markdown(
                f"<div style='display:flex; justify-content:space-between; "
                f"align-items:center; padding:5px 4px; "
                f"border-bottom:1px solid #18181F;'>"
                f"<span style='font-family:JetBrains Mono,monospace; "
                f"font-size:12px; color:#C0C0E0;'>{lang}</span>"
                f"<span style='font-family:JetBrains Mono,monospace; "
                f"font-size:11px; color:#3B82F6;'>{count}</span>"
                f"</div>",
                unsafe_allow_html=True
            )

        st.markdown(
            f"<div style='font-family:Inter,sans-serif; font-size:10px; "
            f"color:#3B3B55; text-align:center; padding:14px 0 4px;'>"
            f"Generated {report['generated_at']}</div>",
            unsafe_allow_html=True
        )


# ─── MAIN DASHBOARD ─────────────────────────────────────────────
def render_dashboard(report: dict):
    # App header bar
    st.markdown(f"""
    <div class="rc-app-header">
        <div class="rc-app-header-name">
            {icon('scan-search', 18, '#3B82F6')}
            Code Review Copilot
            <span class="rc-app-header-tag">v1.0</span>
        </div>
        <div style="font-family:Inter,sans-serif; font-size:12px; color:#7070A0;">
            {icon('folder', 12, '#7070A0')}
            <span style="font-family:JetBrains Mono,monospace; color:#3B82F6;">
                &nbsp;{report['repo_owner']}/{report['repo_name']}
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── RISK SCORE + BREAKDOWNS ──
    col_score, col_sev, col_cat = st.columns([1, 2, 2])

    with col_score:
        st.markdown(
            f"<div class='rc-section-header'>"
            f"{icon('gauge', 14, '#7070A0')} Risk Score</div>",
            unsafe_allow_html=True
        )
        render_score_ring(
            report['repo_score'],
            report['repo_label'],
            report['repo_color']
        )

    with col_sev:
        st.markdown(
            f"<div class='rc-section-header'>"
            f"{icon('layers', 14, '#7070A0')} Severity Breakdown</div>",
            unsafe_allow_html=True
        )
        sev_order = ['Critical', 'High', 'Medium', 'Low', 'Informational']
        for sev in sev_order:
            count = report['severity_counts'].get(sev, 0)
            color = severity_color(sev)
            pct = (count / max(report['total_issues'], 1)) * 100
            st.markdown(
                f"<div style='display:flex; align-items:center; "
                f"gap:10px; margin-bottom:9px;'>"
                f"<div style='width:90px; font-family:Inter,sans-serif; "
                f"font-size:12px; color:#7070A0;'>{sev}</div>"
                f"<div style='flex:1; background:#18181F; border:1px solid #21212B; "
                f"border-radius:3px; height:6px; overflow:hidden;'>"
                f"<div style='width:{pct}%; height:100%; background:{color}; "
                f"border-radius:3px; transition:width 0.6s ease;'></div></div>"
                f"<div style='width:28px; font-family:JetBrains Mono,monospace; "
                f"font-size:12px; font-weight:700; color:{color}; "
                f"text-align:right;'>{count}</div>"
                f"</div>",
                unsafe_allow_html=True
            )

    with col_cat:
        st.markdown(
            f"<div class='rc-section-header'>"
            f"{icon('code-2', 14, '#7070A0')} Category Breakdown</div>",
            unsafe_allow_html=True
        )
        cat_info = {
            'bug':         (icon('bug', 13, '#EF4444'),         'Bugs',        '#EF4444'),
            'security':    (icon('shield-alert', 13, '#F97316'), 'Security',    '#F97316'),
            'performance': (icon('zap', 13, '#EAB308'),          'Performance', '#EAB308'),
            'code_smell':  (icon('code-2', 13, '#3B82F6'),       'Code Smell',  '#3B82F6'),
        }
        for cat, (ico, label, color) in cat_info.items():
            count = report['category_counts'].get(cat, 0)
            pct   = (count / max(report['total_issues'], 1)) * 100
            st.markdown(
                f"<div style='display:flex; align-items:center; "
                f"gap:10px; margin-bottom:9px;'>"
                f"<div style='width:110px; display:flex; align-items:center; "
                f"gap:6px; font-family:Inter,sans-serif; font-size:12px; "
                f"color:#7070A0;'>{ico} {label}</div>"
                f"<div style='flex:1; background:#18181F; border:1px solid #21212B; "
                f"border-radius:3px; height:6px; overflow:hidden;'>"
                f"<div style='width:{pct}%; height:100%; background:{color}; "
                f"border-radius:3px; transition:width 0.6s ease;'></div></div>"
                f"<div style='width:28px; font-family:JetBrains Mono,monospace; "
                f"font-size:12px; font-weight:700; color:{color}; "
                f"text-align:right;'>{count}</div>"
                f"</div>",
                unsafe_allow_html=True
            )

    st.divider()

    # ── SUMMARY METRICS ──
    st.markdown(
        f"<div class='rc-section-header'>"
        f"{icon('layers', 14, '#7070A0')} Summary</div>",
        unsafe_allow_html=True
    )
    m1, m2, m3, m4, m5 = st.columns(5)
    metrics = [
        (m1, "Total Issues",   report['total_issues'],                             None),
        (m2, "Critical",       report['severity_counts'].get('Critical', 0),       None),
        (m3, "Security",       report['category_counts'].get('security', 0),       None),
        (m4, "Files Analyzed", report['files_analyzed'],                           None),
        (m5, "Lines of Code",  f"{report['total_lines_of_code']:,}",               None),
    ]
    for col, label, value, delta in metrics:
        with col:
            st.metric(label, value, delta)

    st.divider()

    # ── HOTSPOTS + CORRELATIONS ──
    col_hot, col_corr = st.columns(2)

    with col_hot:
        st.markdown(
            f"<div class='rc-section-header'>"
            f"{icon('flame', 14, '#7070A0')} Hotspot Files</div>",
            unsafe_allow_html=True
        )
        if report['hotspot_files']:
            max_score = max(h['score'] for h in report['hotspot_files']) or 1
            for h in report['hotspot_files']:
                pct   = (h['score'] / max_score) * 100
                color = h.get('color', '#F97316')
                st.markdown(
                    f"<div class='rc-hotspot-row'>"
                    f"<div class='rc-hotspot-meta'>"
                    f"<span class='rc-hotspot-name'>"
                    f"{icon('file-code-2', 12, '#7070A0')} "
                    f"{h['path'].split('/')[-1]}</span>"
                    f"<span class='rc-hotspot-score'>"
                    f"{h['issue_count']} issues · {h['score']}</span>"
                    f"</div>"
                    f"<div class='rc-hotspot-track'>"
                    f"<div class='rc-hotspot-fill' "
                    f"style='width:{pct}%; background:linear-gradient("
                    f"90deg, {color}99, {color});'></div></div>"
                    f"</div>",
                    unsafe_allow_html=True
                )
        else:
            st.markdown(
                f"<div style='color:#7070A0; font-size:13px;'>"
                f"{icon('circle-check', 14, '#10B981')} "
                f"No hotspots detected.</div>",
                unsafe_allow_html=True
            )

    with col_corr:
        st.markdown(
            f"<div class='rc-section-header'>"
            f"{icon('git-merge', 14, '#7070A0')} Correlations</div>",
            unsafe_allow_html=True
        )
        if report['correlations']:
            for corr in report['correlations'][:4]:
                color = severity_color(corr.get('severity', 'Medium'))
                st.markdown(
                    f"<div class='rc-corr-card' style='border-left-color:{color};'>"
                    f"<div class='rc-corr-title'>{corr['title']}</div>"
                    f"<div class='rc-corr-desc'>{corr['description']}</div>"
                    f"<div class='rc-corr-meta'>"
                    f"{icon('file-code-2', 10, '#3B3B55')} "
                    f"{len(corr['affected_files'])} file(s) affected"
                    f"</div></div>",
                    unsafe_allow_html=True
                )
        else:
            st.markdown(
                f"<div style='color:#7070A0; font-size:13px;'>"
                f"{icon('circle-check', 14, '#10B981')} "
                f"No cross-file correlations detected.</div>",
                unsafe_allow_html=True
            )

    st.divider()

    # ── FINDINGS ──
    st.markdown(
        f"<div class='rc-section-header'>"
        f"{icon('bug', 14, '#7070A0')} Findings</div>",
        unsafe_allow_html=True
    )

    # Filters
    f1, f2, f3, f4 = st.columns([2, 1, 1, 1])
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
        sort_by = st.selectbox(
            "Sort by",
            ['Severity', 'File', 'Category']
        )

    filtered = filter_issues(
        report['all_issues'],
        severity=selected_sev,
        category=selected_cat,
        file_path=selected_file,
    )

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
        f"<div style='font-family:JetBrains Mono,monospace; font-size:11px; "
        f"color:#3B3B55; margin-bottom:14px;'>"
        f"Showing {len(filtered)} of {report['total_issues']} issues</div>",
        unsafe_allow_html=True
    )

    if filtered:
        for idx, issue in enumerate(filtered):
            render_issue_card(issue, idx)
    else:
        st.markdown(
            f"<div style='text-align:center; padding:40px; color:#7070A0;'>"
            f"{icon('circle-check', 20, '#10B981')} "
            f"No issues match your filters.</div>",
            unsafe_allow_html=True
        )


# ─── LANDING PAGE ────────────────────────────────────────────────
def render_landing():
    # Hero
    scan_svg = icon('scan-search', 48, '#3B82F6')
    st.markdown(f"""
    <div style='text-align:center; padding:64px 20px 36px;'>
        <div style='margin-bottom:18px;'>{scan_svg}</div>
        <h1 style='
            font-family: Space Grotesk, sans-serif;
            font-size: 38px;
            font-weight: 700;
            letter-spacing: -0.03em;
            background: linear-gradient(135deg, #F0F0F5 30%, #3B82F6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 14px;
            line-height: 1.15;
        '>Code Review Copilot</h1>
        <p style='
            font-family: Inter, sans-serif;
            font-size: 15px;
            color: #7070A0;
            max-width: 460px;
            margin: 0 auto 36px;
            line-height: 1.75;
        '>
            AI-powered static analysis for any GitHub repository.
            Detect bugs, vulnerabilities, performance issues,
            and code smells — in seconds.
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
            analyze = st.button(
                f"Analyze Repository",
                use_container_width=True
            )
        with col_opt:
            github_token = st.text_input(
                "GitHub Token",
                type="password",
                placeholder="ghp_...  (optional, for private repos)",
                label_visibility="collapsed",
            )

    # Feature pills
    pill_items = [
        ('bug',          '#EF4444', 'Bug Detection'),
        ('shield-alert', '#F97316', 'Security Analysis'),
        ('zap',          '#EAB308', 'Performance Review'),
        ('code-2',       '#3B82F6', 'Code Smell Detection'),
        ('git-merge',    '#7070A0', 'Correlation Engine'),
    ]
    pills_html = "<div class='rc-pill-row'>"
    for ico_name, color, label in pill_items:
        pills_html += (
            f"<span class='rc-badge' style='background:rgba(255,255,255,0.04); "
            f"color:#7070A0; border:1px solid #21212B;'>"
            f"{icon(ico_name, 12, color)} {label}</span>"
        )
    pills_html += "</div>"
    st.markdown(pills_html, unsafe_allow_html=True)

    return github_url, analyze, github_token


# ─── ANALYSIS PIPELINE ──────────────────────────────────────────
def run_analysis(github_url: str, token: str = None):
    log_messages = []

    def log(msg):
        log_messages.append(msg)
        # strip emoji from log messages, use monospace styling
        status_text.markdown(
            f"<div style='font-family:JetBrains Mono,monospace; font-size:12px; "
            f"color:#7070A0; padding:4px 0;'>{msg}</div>",
            unsafe_allow_html=True
        )

    progress = st.progress(0)
    status_text = st.empty()

    try:
        log("→  Connecting to GitHub...")
        repo_data = ingest_repository(github_url, token, log)
        progress.progress(20)

        if not repo_data['files']:
            st.error("No analyzable files found in this repository.")
            return None

        log("→  Parsing code structure...")
        parsed_files = parse_all_files(repo_data['files'])
        structure_summary = get_repo_structure_summary(parsed_files)
        progress.progress(35)

        log(f"→  Running AI analysis on {len(parsed_files)} files...")
        analysis_results = analyze_repository(parsed_files, log)
        progress.progress(75)

        scoring_data = score_all_results(analysis_results)
        progress.progress(90)

        # ── Check whether any file hit the exhausted-keys wall ───────
        rate_limited = [
            r for r in analysis_results
            if r.get('analysis_status') == 'rate_limited'
        ]
        successful = [
            r for r in analysis_results
            if r.get('analysis_status') == 'success'
        ]

        if rate_limited:
            from src.analyzer import _ALL_KEYS
            key_count = len(_ALL_KEYS)
            progress.empty()
            status_text.empty()
            st.markdown(f"""
            <div style="background:rgba(234,179,8,0.08);border:1px solid rgba(234,179,8,0.35);
                border-left:3px solid #EAB308;border-radius:6px;padding:16px 20px;margin:12px 0;
                font-family:Inter,sans-serif;">
                <div style="font-family:Space Grotesk,sans-serif;font-size:13px;font-weight:600;
                    color:#EAB308;margin-bottom:8px;">
                    ⚠ All Groq API Keys Exhausted
                </div>
                <div style="font-size:13px;color:#C0A840;line-height:1.7;">
                    All <strong style="color:#EAB308;">{key_count}</strong> key(s) hit the
                    100k token/day limit. &nbsp;
                    <strong style="color:#EAB308;">{len(successful)}</strong> of
                    <strong style="color:#EAB308;">{len(analysis_results)}</strong>
                    files were analyzed. Results below are partial.
                </div>
                <div style="margin-top:10px;font-family:JetBrains Mono,monospace;
                    font-size:12px;color:#7070A0;">
                    Add fresh keys as GROQ_API_KEY_1 / _2 / _3 in .env and restart.
                </div>
            </div>
            """, unsafe_allow_html=True)
            if not successful:
                return None



        

        log("→  Building report...")
        report = build_full_report(scoring_data, repo_data, structure_summary)
        progress.progress(100)

        log("✓  Analysis complete.")
        time.sleep(0.5)
        progress.empty()
        status_text.empty()

        return report

    except ValueError as e:
        st.error(f"{str(e)}")
        progress.empty()
        status_text.empty()
        return None

    except Exception as e:
        st.error(f"Unexpected error: {str(e)}")
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
            with st.spinner(""):
                report = run_analysis(github_url, token or None)
                if report:
                    st.session_state.report = report
                    st.rerun()
        elif analyze and not github_url:
            st.warning("Please enter a GitHub repository URL.")

    else:
        report = st.session_state.report
        render_sidebar(report)
        render_dashboard(report)

        with st.sidebar:
            st.markdown(
                "<div style='border-top:1px solid #21212B; margin:8px 0;'></div>",
                unsafe_allow_html=True
            )
            if st.button(
                f"Analyze New Repo",
                use_container_width=True
            ):
                st.session_state.report = None
                st.rerun()


if __name__ == "__main__":
    main()