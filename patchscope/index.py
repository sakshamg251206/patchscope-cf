"""Gold-blind AST file index. No issue text, patch or labels enter this module."""
import ast
from dataclasses import dataclass
import re

import networkx as nx

TEXT_CAP = 24_000


def tokenize(text: str) -> list[str]:
    text = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', text)
    text = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', text)
    return re.findall(r'[a-z]+|[0-9]+', text.lower())


@dataclass
class Index:
    paths: list[str]
    tokens: list[list[str]]
    graph: nx.DiGraph
    audit: dict


def module_name(path: str) -> str:
    parts = path[:-3].split('/')
    if len(parts) > 1 and parts[0] in {'src', 'lib'}:
        parts = parts[1:]
    return '.'.join(parts)


def build_index(files: dict[str, str]) -> Index:
    paths = sorted(files)
    modules = {}
    for path in paths:
        module = module_name(path)
        if module.endswith('.__init__'):
            module = module[:-9]
        modules[module] = path
    graph = nx.DiGraph()
    graph.add_nodes_from(paths)
    documents, failures = [], []
    for path in paths:
        module = module_name(path)
        package = module.split('.')[:-1]
        parts = [path, module]
        imports = set()
        try:
            tree = ast.parse(files[path])
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    parts.append(node.name)
                if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    doc = ast.get_docstring(node)
                    if doc:
                        parts.append(doc)
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        parts.append(alias.name)
                        imports.add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.level:
                        if node.level > len(package):
                            continue
                        prefix = package[:len(package) - node.level + 1]
                        base = '.'.join(prefix + ([node.module] if node.module else []))
                    else:
                        base = node.module or ''
                    parts.append(base)
                    # Prefer imported submodule; otherwise the containing module.
                    for alias in node.names:
                        parts.append(alias.name)
                        child = f'{base}.{alias.name}' if base else alias.name
                        imports.add(child if child in modules else base)
        except (SyntaxError, ValueError, RecursionError):
            failures.append(path)
        for target in sorted(imports):
            if target in modules and modules[target] != path:
                graph.add_edge(path, modules[target], kind='import', confidence='static_exact_module')
        documents.append(tokenize('\n'.join(parts)[:TEXT_CAP]))
    return Index(paths, documents, graph, dict(parse_failures=failures,
                 text_cap=TEXT_CAP, construction='path + module + AST names/imports/docstrings; no source snippets',
                 tokenizer='camel/acronym/snake split; lowercase ASCII letters/digits; no stopwords'))
