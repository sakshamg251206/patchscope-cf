"""Paired evaluation; labels are used only here and in diagnostic masking."""
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import time

import numpy as np

from .data import freeze_selection, snapshot, write_json
from .graph import edge_drop, load_edges, rewire
from .index import build_index, tokenize
from .labels import gold_paths
from .masking import mask_query
from .retrieve import BM25, rank

METRICS = ('hit1', 'hit5', 'hit10', 'mrr10', 'recall5', 'recall10')


def metrics(predicted: list[str], gold: list[str]) -> dict[str, float]:
    if not gold:
        raise ValueError('gold cannot be empty')
    labels = set(gold)
    first = next((i+1 for i, path in enumerate(predicted[:10]) if path in labels), None)
    return dict(hit1=float(bool(labels.intersection(predicted[:1]))),
                hit5=float(bool(labels.intersection(predicted[:5]))),
                hit10=float(bool(labels.intersection(predicted[:10]))),
                mrr10=1/first if first else 0.,
                recall5=len(labels.intersection(predicted[:5]))/len(labels),
                recall10=len(labels.intersection(predicted[:10]))/len(labels))


def paired_bootstrap(real, control, seed=2026, replicates=2000):
    real, control = np.asarray(real, dtype=float), np.asarray(control, dtype=float)
    if real.shape != control.shape or real.ndim != 1 or not len(real):
        raise ValueError('paired nonempty vectors with matching shape required')
    difference = real - control
    rng = np.random.default_rng(seed)
    estimates = difference[rng.integers(0, len(real), size=(replicates, len(real)))].mean(axis=1)
    low, high = np.quantile(estimates, [.025, .975])
    return dict(n=len(real), difference_pp=float(difference.mean()*100),
                lower_pp=float(low*100), upper_pp=float(high*100))


def write_csv(path: Path, rows: list[dict], fields=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    with temporary.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields or list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def evaluate_case(case, index, gold, seed, budget=100, seeds=20, alpha=.5):
    start = time.perf_counter()
    model = BM25(index.tokens)
    bm25_build_ms = (time.perf_counter()-start)*1000
    variants = [('bm25', 0, None), ('real', 0, index.graph)]
    controls = []
    start = time.perf_counter()
    for control_seed in (seed, seed+1, seed+2):
        graph, stats = rewire(index.graph, control_seed)
        controls.append(stats)
        variants.append(('rewired', control_seed, graph))
    variants.append(('edge_drop', seed, edge_drop(index.graph, seed)))
    control_build_ms = (time.perf_counter()-start)*1000
    masked, spans = mask_query(case['problem_statement'], gold, index.paths)
    rows = []
    for condition, query in [('raw', case['problem_statement']), ('masked', masked)]:
        # Shared lexical work is charged equally to each variant; graph creation is offline.
        lexical_times = []
        for _ in range(3):
            start = time.perf_counter()
            scores = model.scores(tokenize(query))
            lexical_times.append((time.perf_counter()-start)*1000)
        baseline = rank(index.paths, scores, None, budget, seeds, alpha)
        for method, control_seed, graph in variants:
            times = []
            for _ in range(3):
                start = time.perf_counter()
                predicted = rank(index.paths, scores, graph, budget, seeds, alpha)
                times.append((time.perf_counter()-start)*1000)
            assert set(predicted) == set(baseline)
            assert len(predicted) == min(budget, len(index.paths))
            assert len(set(predicted)) == len(predicted)
            assert predicted == rank(index.paths, scores, graph, budget, seeds, alpha)
            assert rank(index.paths, scores, graph, budget, seeds, 0) == baseline
            rows.append(dict(instance_id=case['instance_id'], repo=case['repo'],
                base_commit=case['base_commit'], method=method, condition=condition,
                seed=control_seed, num_files=len(index.paths), num_edges=index.graph.number_of_edges(),
                method_edges=graph.number_of_edges() if graph is not None else 0,
                num_gold=len(gold), gold_paths=json.dumps(gold),
                predicted_paths=json.dumps(predicted), **metrics(predicted, gold),
                query_ms=float(np.median(lexical_times)+np.median(times)),
                candidate_budget=budget, seed_budget=seeds, alpha=alpha))
    return rows, dict(mask_spans=spans, mask_changed=bool(spans),
                     query_sha256=hashlib.sha256(case['problem_statement'].encode()).hexdigest(),
                     rewiring=controls, bm25_build_ms=bm25_build_ms,
                     control_build_ms=control_build_ms)


def run_evaluation(rows, revision, sample, seed, output: Path, cache: Path, split,
                   snapshot_provider=snapshot, manifest_path: Path | None = None,
                   graph_edges: Path | None = None):
    """Run the counterfactual localization audit.

    `graph_edges` points at a directory of externally supplied code graphs, one
    `<instance_id>.csv` or `<instance_id>.json` per issue (see `graph.load_edges`). It
    replaces the built-in import graph so any code graph can be measured against its own
    degree-preserving null. Left as None, the built-in import graph is used and nothing in
    this function's behaviour changes.
    """
    output.mkdir(parents=True, exist_ok=True)
    if (output / 'experiment_config.json').exists():
        raise FileExistsError(f'results already exist in {output}; use a fresh output directory')
    selected = freeze_selection(rows, sample, seed, manifest_path or output/'selection_manifest.json', revision, split)
    config = dict(started_at_utc=datetime.now(timezone.utc).isoformat(),
                  revision=revision, split=split, requested=sample, seed=seed,
                  candidate_budget=100, seed_budget=20, alpha=.5, rewiring_seeds=[seed,seed+1,seed+2],
                  bootstrap_replicates=2000, query_repetitions=3,
                  python=platform.python_version(), platform=platform.platform(), machine=platform.machine(),
                  protocol='fixed a priori; no test tuning; pool-identical one-hop outgoing-import reranking',
                  graph_source=str(graph_edges) if graph_edges else 'builtin_import_graph',
                  index='AST names/imports/docstrings + path/module; 24000 chars per file',
                  timing='median of 3 warm lexical + median of 3 ranking times; graph prep excluded',
                  dependency_versions={},
                  source_code_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                      for p in sorted(Path(__file__).parent.glob('*.py'))})
    from importlib.metadata import version
    config['dependency_versions'] = {p: version(p) for p in ['numpy','networkx','matplotlib','pyarrow','certifi']}
    write_json(output/'experiment_config.json', config)
    results, exclusions, audits = [], [], []
    for i, case in enumerate(selected):
        print(f'[{i+1}/{sample}] {case["instance_id"]}', flush=True)
        try:
            start = time.perf_counter()
            files, source_audit = snapshot_provider(case['repo'], case['base_commit'], cache)
            snapshot_ms = (time.perf_counter()-start)*1000
            labels = gold_paths(case['patch'])
            gold = [path for path in labels if path in files]
            if not labels:
                raise ValueError('no eligible source labels')
            # Require ALL filtered labels present; never quietly shrink the gold set.
            if len(gold) != len(labels):
                raise ValueError('source labels absent at base commit: ' + json.dumps(sorted(set(labels)-set(gold))))
            start = time.perf_counter()
            index = build_index(files)
            ast_ms = (time.perf_counter()-start)*1000
            external = None
            if graph_edges is not None:
                supplied = [c for ext in ('.csv', '.json')
                            for c in [graph_edges / f'{case["instance_id"]}{ext}'] if c.exists()]
                if not supplied:
                    raise ValueError(f'no supplied graph for {case["instance_id"]} in {graph_edges}')
                index.graph, external = load_edges(supplied[0], index.paths)
            case_rows, audit = evaluate_case(case, index, gold, seed)
            case_audit = dict(instance_id=case['instance_id'], repo=case['repo'], base_commit=case['base_commit'],
                             source=source_audit, index=index.audit, snapshot_ms=snapshot_ms,
                             ast_build_ms=ast_ms, num_files=len(files), num_edges=index.graph.number_of_edges(),
                             isolates=sum(index.graph.degree(n)==0 for n in index.graph),
                             gold_in_degree=[index.graph.in_degree(g) for g in gold],
                             gold_out_degree=[index.graph.out_degree(g) for g in gold], **audit)
            if external is not None:
                case_audit['external_graph'] = external
            audits.append(case_audit)
            results.extend(case_rows)
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            exclusions.append(dict(instance_id=case['instance_id'], repo=case['repo'],
                                   base_commit=case['base_commit'], reason=f'{type(exc).__name__}: {exc}'))
            print('  EXCLUDED:', exclusions[-1]['reason'], flush=True)
        # Full prefixes are checkpointed after each case; partial runs are marked incomplete.
        if results:
            write_csv(output/'per_instance.csv', results)
        write_csv(output/'exclusions.csv', exclusions, ['instance_id','repo','base_commit','reason'])
        write_json(output/'audit.json', audits)
    config.update(finished_at_utc=datetime.now(timezone.utc).isoformat(),
                  eligible=len(audits), excluded=len(exclusions), completed=True,
                  repos=sorted({a['repo'] for a in audits}))
    write_json(output/'experiment_config.json', config)
    manifest_file = manifest_path or output/'selection_manifest.json'
    manifest = json.loads(manifest_file.read_text())
    reasons = {r['instance_id']: r['reason'] for r in exclusions}
    manifest['outcomes'] = [dict(instance_id=case['instance_id'],
                                status='excluded' if case['instance_id'] in reasons else 'included',
                                reason=reasons.get(case['instance_id'], 'all source gold paths present at base; all methods completed'))
                            for case in selected]
    write_json(manifest_file, manifest)
    return config
