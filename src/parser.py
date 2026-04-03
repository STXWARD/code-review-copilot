import ast
import re
from pathlib import Path


def parse_python(content: str) -> dict:
    """
    Use Python's built-in AST to extract structure from Python files.
    Most accurate parser we have — Python analyzing Python.
    """
    structure = {
        'functions': [],
        'classes': [],
        'imports': [],
        'complexity_score': 0,
    }

    try:
        tree = ast.parse(content)
    except SyntaxError:
        # File has syntax errors — still return empty structure
        return structure

    for node in ast.walk(tree):

        # Extract functions
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func_lines = (node.end_lineno or 0) - node.lineno
            structure['functions'].append({
                'name': node.name,
                'line_start': node.lineno,
                'line_end': node.end_lineno or node.lineno,
                'line_count': func_lines,
                'args': [a.arg for a in node.args.args],
                'is_async': isinstance(node, ast.AsyncFunctionDef),
                'too_long': func_lines > 50,
            })

        # Extract classes
        elif isinstance(node, ast.ClassDef):
            structure['classes'].append({
                'name': node.name,
                'line_start': node.lineno,
                'line_end': node.end_lineno or node.lineno,
                'methods': [
                    n.name for n in ast.walk(node)
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                ],
            })

        # Extract imports
        elif isinstance(node, ast.Import):
            for alias in node.names:
                structure['imports'].append(alias.name)

        elif isinstance(node, ast.ImportFrom):
            module = node.module or ''
            structure['imports'].append(module)

    # Rough complexity: count branches
    branch_nodes = (
        ast.If, ast.For, ast.While, ast.Try,
        ast.ExceptHandler, ast.With
    )
    branch_count = sum(
        1 for node in ast.walk(tree)
        if isinstance(node, branch_nodes)
    )
    structure['complexity_score'] = branch_count

    return structure


def parse_generic(content: str, language: str) -> dict:
    """
    Regex-based parser for non-Python files.
    Less accurate than AST but works across languages.
    """
    structure = {
        'functions': [],
        'classes': [],
        'imports': [],
        'complexity_score': 0,
    }

    lines = content.split('\n')

    # Language-specific patterns
    patterns = {
        'JavaScript': {
            'function': r'(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\()',
            'class': r'class\s+(\w+)',
            'import': r'(?:import|require)\s*[\(\{]?\s*[\'"]([^\'"]+)[\'"]',
        },
        'TypeScript': {
            'function': r'(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\()',
            'class': r'class\s+(\w+)',
            'import': r'import\s+.*from\s+[\'"]([^\'"]+)[\'"]',
        },
        'Java': {
            'function': r'(?:public|private|protected|static|\s)+[\w<>\[\]]+\s+(\w+)\s*\(',
            'class': r'(?:public|private|protected)?\s*class\s+(\w+)',
            'import': r'import\s+([\w.]+);',
        },
        'Go': {
            'function': r'func\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)\s*\(',
            'class': r'type\s+(\w+)\s+struct',
            'import': r'"([\w./]+)"',
        },
        'Ruby': {
            'function': r'def\s+(\w+)',
            'class': r'class\s+(\w+)',
            'import': r'require\s+[\'"]([^\'"]+)[\'"]',
        },
    }

    # Default pattern for unknown languages
    default_patterns = {
        'function': r'(?:function|def|func)\s+(\w+)',
        'class': r'class\s+(\w+)',
        'import': r'(?:import|include|require)\s+[\'"]?(\w+)',
    }

    lang_patterns = patterns.get(language, default_patterns)

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Functions
        func_match = re.search(lang_patterns['function'], stripped)
        if func_match:
            name = next(
                (g for g in func_match.groups() if g), 'anonymous'
            )
            structure['functions'].append({
                'name': name,
                'line_start': i,
                'line_end': i,
                'line_count': 0,
                'args': [],
                'is_async': 'async' in stripped,
                'too_long': False,
            })

        # Classes
        class_match = re.search(lang_patterns['class'], stripped)
        if class_match:
            structure['classes'].append({
                'name': class_match.group(1),
                'line_start': i,
                'line_end': i,
                'methods': [],
            })

        # Imports
        import_match = re.search(lang_patterns['import'], stripped)
        if import_match:
            structure['imports'].append(import_match.group(1))

    # Rough complexity from keywords
    complexity_keywords = [
        'if ', 'else ', 'elif ', 'for ', 'while ',
        'try ', 'catch ', 'except ', 'switch ', 'case '
    ]
    structure['complexity_score'] = sum(
        1 for line in lines
        for kw in complexity_keywords
        if kw in line.lower()
    )

    return structure


def parse_file(file_data: dict) -> dict:
    """
    Main parser — routes to correct parser based on language.
    Enriches file_data with structural info.
    """
    result = file_data.copy()
    language = file_data.get('language', 'Unknown')
    content = file_data.get('content', '')

    if language == 'Python':
        structure = parse_python(content)
    else:
        structure = parse_generic(content, language)

    result['structure'] = structure
    result['total_functions'] = len(structure['functions'])
    result['total_classes'] = len(structure['classes'])
    result['complexity_score'] = structure['complexity_score']

    # Flag long functions as a quick code smell signal
    result['long_functions'] = [
        f for f in structure['functions']
        if f.get('too_long')
    ]

    return result
def parse_all_files(files: list) -> list:
    """Parse structure from all files."""
    return [parse_file(f) for f in files]


def get_repo_structure_summary(parsed_files: list) -> dict:
    """Build a high-level summary of the entire repository structure."""
    all_functions = []
    all_classes = []
    all_imports = []
    total_complexity = 0
    language_breakdown = {}

    for f in parsed_files:
        structure = f.get('structure', {})
        lang = f.get('language', 'Unknown')

        all_functions.extend([
            {**fn, 'file': f['path']}
            for fn in structure.get('functions', [])
        ])
        all_classes.extend([
            {**cls, 'file': f['path']}
            for cls in structure.get('classes', [])
        ])
        all_imports.extend(structure.get('imports', []))
        total_complexity += structure.get('complexity_score', 0)
        language_breakdown[lang] = language_breakdown.get(lang, 0) + 1

    import_freq = {}
    for imp in all_imports:
        import_freq[imp] = import_freq.get(imp, 0) + 1

    top_imports = sorted(
        import_freq.items(), key=lambda x: x[1], reverse=True
    )[:10]

    return {
        'total_functions': len(all_functions),
        'total_classes': len(all_classes),
        'total_complexity': total_complexity,
        'language_breakdown': language_breakdown,
        'top_imports': top_imports,
        'long_functions': [
            f for f in all_functions if f.get('too_long')
        ],
    }

