import requests
import base64
import os
from pathlib import Path

SKIP_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.webp',
    '.pdf', '.zip', '.tar', '.gz', '.rar',
    '.lock', '.sum',
    '.woff', '.woff2', '.ttf', '.eot',
    '.mp4', '.mp3', '.wav',
    '.pyc', '.pyo', '.pyd',
    '.exe', '.dll', '.so', '.bin',
    '.csv', '.parquet', '.pkl',
}

SKIP_DIRS = {
    'node_modules', '__pycache__', '.git', 'venv', 'env',
    'dist', 'build', '.next', '.nuxt', 'coverage',
    '.pytest_cache', '.mypy_cache', 'eggs', '.eggs',
    'vendor', 'third_party', 'extern', 'external',
}

MAX_FILE_SIZE_KB = 60
MAX_LINES = 600


def parse_github_url(url: str):
    """Extract owner and repo name from GitHub URL."""
    url = url.strip().rstrip('/')
    url = url.replace('https://github.com/', '')
    url = url.replace('http://github.com/', '')
    parts = url.split('/')
    if len(parts) < 2:
        raise ValueError("Invalid GitHub URL. Format: https://github.com/owner/repo")
    return parts[0], parts[1]


def fetch_repo_tree(owner: str, repo: str, token: str = None):
    """Fetch full file tree of the repo using GitHub API."""
    headers = {'Accept': 'application/vnd.github.v3+json'}
    if token:
        headers['Authorization'] = f'token {token}'

    # Get default branch first
    repo_url = f'https://api.github.com/repos/{owner}/{repo}'
    resp = requests.get(repo_url, headers=headers, timeout=10)

    if resp.status_code == 404:
        raise ValueError(f"Repository '{owner}/{repo}' not found or is private.")
    if resp.status_code == 403:
        raise ValueError("GitHub API rate limit hit. Add a GitHub token to continue.")
    resp.raise_for_status()

    default_branch = resp.json().get('default_branch', 'main')

    # Get full tree recursively
    tree_url = f'https://api.github.com/repos/{owner}/{repo}/git/trees/{default_branch}?recursive=1'
    tree_resp = requests.get(tree_url, headers=headers, timeout=15)
    tree_resp.raise_for_status()

    return tree_resp.json().get('tree', []), default_branch


def should_skip(path: str) -> bool:
    """Return True if this file should be skipped."""
    p = Path(path)

    # Skip by directory
    for part in p.parts:
        if part in SKIP_DIRS:
            return True

    # Skip by extension
    if p.suffix.lower() in SKIP_EXTENSIONS:
        return True

    # Skip hidden files
    if p.name.startswith('.'):
        return True

    return False


def fetch_file_content(owner: str, repo: str, path: str,
                        branch: str, token: str = None) -> str | None:
    """Fetch and decode content of a single file."""
    headers = {'Accept': 'application/vnd.github.v3+json'}
    if token:
        headers['Authorization'] = f'token {token}'

    url = f'https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={branch}'
    resp = requests.get(url, headers=headers, timeout=10)

    if resp.status_code != 200:
        return None

    data = resp.json()
    size_kb = data.get('size', 0) / 1024

    if size_kb > MAX_FILE_SIZE_KB:
        return None  # skip large files

    encoding = data.get('encoding', '')
    content = data.get('content', '')

    if encoding == 'base64':
        try:
            decoded = base64.b64decode(content).decode('utf-8', errors='ignore')
            # Trim to max lines
            lines = decoded.split('\n')
            if len(lines) > MAX_LINES:
                decoded = '\n'.join(lines[:MAX_LINES])
                decoded += f'\n\n# ... truncated at {MAX_LINES} lines'
            return decoded
        except Exception:
            return None

    return None


def detect_language(path: str) -> str:
    """Detect programming language from file extension."""
    from pathlib import Path
    
    # Handle special filenames first (no extension)
    filename = Path(path).name.lower()
    special_files = {
        '.gitignore':       'Config',
        '.gitattributes':   'Config',
        '.prettierrc':      'Config',
        '.eslintrc':        'Config',
        '.babelrc':         'Config',
        '.editorconfig':    'Config',
        '.env':             'Config',
        'dockerfile':       'Docker',
        'makefile':         'Makefile',
    }
    if filename in special_files:
        return special_files[filename]

    # Handle files with no extension
    if not Path(path).suffix:
        return 'Config'

    ext_map = {
        # Languages
        '.py':      'Python',
        '.js':      'JavaScript',
        '.jsx':     'JavaScript (React)',
        '.ts':      'TypeScript',
        '.tsx':     'TypeScript (React)',
        '.java':    'Java',
        '.cpp':     'C++',
        '.c':       'C',
        '.cs':      'C#',
        '.go':      'Go',
        '.rs':      'Rust',
        '.rb':      'Ruby',
        '.php':     'PHP',
        '.swift':   'Swift',
        '.kt':      'Kotlin',
        '.scala':   'Scala',
        '.r':       'R',
        '.sql':     'SQL',
        '.sh':      'Shell',
        '.bash':    'Shell',
        '.ps1':     'PowerShell',
        # Web
        '.html':    'HTML',
        '.htm':     'HTML',
        '.css':     'CSS',
        '.scss':    'SCSS',
        '.sass':    'SASS',
        '.vue':     'Vue',
        '.svelte':  'Svelte',
        # Config / Data
        '.json':    'JSON',
        '.yaml':    'YAML',
        '.yml':     'YAML',
        '.toml':    'TOML',
        '.xml':     'XML',
        '.csv':     'CSV',
        '.ini':     'Config',
        '.cfg':     'Config',
        '.lock':    'Config',
        '.env':     'Config',
        # Docs
        '.md':      'Markdown',
        '.mdx':     'Markdown',
        '.txt':     'Text',
        '.ipynb':   'Jupyter Notebook',
    }

    suffix = Path(path).suffix.lower()
    return ext_map.get(suffix, 'Unknown')


def ingest_repository(github_url: str, token: str = None,
                       progress_callback=None) -> dict:
    token = token or os.getenv("GITHUB_TOKEN")
    """
    Main function — takes a GitHub URL and returns
    a structured dict of all analyzable files.
    """
    owner, repo = parse_github_url(github_url)

    if progress_callback:
        progress_callback(f"📡 Connecting to GitHub: {owner}/{repo}")

    tree, branch = fetch_repo_tree(owner, repo, token)

    # Filter to only blob (file) nodes
    all_files = [node for node in tree if node['type'] == 'blob']

    # Filter out files we should skip
    analyzable = [f for f in all_files if not should_skip(f['path'])]

    if progress_callback:
        progress_callback(
            f"📁 Found {len(all_files)} files — "
            f"{len(analyzable)} selected for analysis"
        )

    
# Fetch content for each file in parallel
    from concurrent.futures import ThreadPoolExecutor, as_completed

    files_data = []

    def fetch_single(file_node):
        path = file_node['path']
        language = detect_language(path)
        content = fetch_file_content(owner, repo, path, branch, token)
        if content and content.strip():
            return {
                'path': path,
                'language': language,
                'content': content,
                'size_lines': len(content.split('\n')),
            }
        return None

    if progress_callback:
        progress_callback(f"⬇️ Fetching {len(analyzable)} files in parallel...")

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(fetch_single, f): f for f in analyzable}
        completed = 0
        for future in as_completed(futures):
            result = future.result()
            completed += 1
            if result:
                files_data.append(result)
                if progress_callback:
                    progress_callback(
                        f"⬇️ ({completed}/{len(analyzable)}) "
                        f"Fetched: {result['path']}"
                    )

    # Build language summary
    lang_summary = {}
    for f in files_data:
        lang = f['language']
        lang_summary[lang] = lang_summary.get(lang, 0) + 1

    return {
        'owner': owner,
        'repo': repo,
        'branch': branch,
        'total_files_in_repo': len(all_files),
        'files_analyzed': len(files_data),
        'languages': lang_summary,
        'files': files_data,
    }