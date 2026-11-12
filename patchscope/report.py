"""Tables, paired uncertainty, slices and plots derived only from result rows."""
from collections import defaultdict
import csv
import json
from pathlib import Path

import numpy as np

from .evaluate import METRICS, paired_bootstrap, write_csv
from .data import write_json

METHODS = ('bm25', 'real', 'rewired', 'edge_drop')


def read_rows(path):
    with Path(path).open() as handle:
        return list(csv.DictReader(handle))


def _group(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[(row['condition'],row['method'],row['instance_id'])].append(row)
    condition_cohorts = [{row['instance_id'] for row in rows if row['condition']==condition}
                         for condition in {row['condition'] for row in rows}]
    if condition_cohorts and any(c != condition_cohorts[0] for c in condition_cohorts):
        raise ValueError('raw/masked cohort mismatch')
    for (_, method, _), values in groups.items():
        if len({str(r['seed']) for r in values}) != len(values):
            raise ValueError('duplicate method seed')
    # Prevent treating missing seeds/cases as a different denominator.
    for condition in {row['condition'] for row in rows}:
        cohorts = [{instance for c,m,instance in groups if c==condition and m==method} for method in METHODS]
        if not all(cohort == cohorts[0] for cohort in cohorts):
            raise ValueError('method cohort mismatch')
        for method in METHODS:
            counts = [len(values) for (c,m,_),values in groups.items() if c==condition and m==method]
            if any(n != (3 if method=='rewired' else 1) for n in counts):
                raise ValueError('incomplete method/seed cohort')
    return groups


def summarize(rows):
    groups = _group(rows)
    summary = []
    for condition in sorted({row['condition'] for row in rows}):
        for method in METHODS:
            cases = [values for (c,m,_),values in groups.items() if c==condition and m==method]
            values = {metric: float(np.mean([np.mean([float(r[metric]) for r in case]) for case in cases]))
                      for metric in METRICS}
            times = [np.mean([float(r['query_ms']) for r in case]) for case in cases]
            summary.append(dict(condition=condition,method=method,n=len(cases),**values,
                                query_median_ms=float(np.median(times)),query_p95_ms=float(np.quantile(times,.95))))
    return summary


def paired_comparisons(rows):
    groups = _group(rows)
    output = []
    for condition in sorted({row['condition'] for row in rows}):
        ids = sorted({row['instance_id'] for row in rows if row['condition']==condition})
        for control in ('bm25','rewired','edge_drop'):
            for metric in METRICS:
                values = lambda m: [np.mean([float(row[metric]) for row in groups[(condition,m,i)]]) for i in ids]
                output.append(dict(condition=condition,method='real',control=control,metric=metric,
                                   **paired_bootstrap(values('real'),values(control))))
    return output


def markdown_table(summary):
    lines = ['| Condition | Method | n | Hit@1 | Hit@5 | Hit@10 | MRR@10 | Recall@5 | Median / P95 ms |',
             '|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in summary:
        lines.append(f"| {r['condition']} | {r['method']} | {r['n']} | {100*r['hit1']:.1f}% | {100*r['hit5']:.1f}% | {100*r['hit10']:.1f}% | {r['mrr10']:.3f} | {100*r['recall5']:.1f}% | {r['query_median_ms']:.2f} / {r['query_p95_ms']:.2f} |")
    return '\n'.join(lines)


def generate_report(directory: Path):
    directory = Path(directory)
    config = json.loads((directory/'experiment_config.json').read_text())
    if not config.get('completed'):
        raise ValueError('cannot report an incomplete run')
    rows = read_rows(directory/'per_instance.csv')
    summary = summarize(rows)
    if any(r['n'] != config['eligible'] for r in summary):
        raise ValueError('result denominator differs from completed config')
    write_csv(directory/'summary.csv', summary)
    paired = paired_comparisons(rows)
    write_csv(directory/'paired_comparisons.csv', paired)
    (directory/'RESULTS.md').write_text(markdown_table(summary)+'\n')
    audits = json.loads((directory/'audit.json').read_text())
    offline=[]
    for a in audits:
        offline.append({k:a[k] for k in ['instance_id','repo','num_files','num_edges','snapshot_ms','ast_build_ms','bm25_build_ms','control_build_ms','isolates']})
    write_csv(directory/'offline_times.csv',offline)
    # Descriptive slices only: no subgroup significance claims or tuning.
    for key in ['repo','num_gold']:
        slices=[]
        for value in sorted({str(r[key]) for r in rows}):
            subset=[r for r in rows if str(r[key])==value]
            slices.extend([{key:value,**r} for r in summarize(subset)])
        write_csv(directory/f'by_{key}.csv',slices)
    coverage={a['instance_id']: ('zero_gold_import_degree' if not sum(a['gold_in_degree'])+sum(a['gold_out_degree']) else 'nonzero_gold_import_degree') for a in audits}
    slices=[]
    for value in sorted(set(coverage.values())):
        slices.extend([{'coverage':value,**r} for r in summarize([r for r in rows if coverage[r['instance_id']]==value])])
    write_csv(directory/'by_coverage.csv',slices)
    leakage = dict(n=len(audits), changed=sum(a['mask_changed'] for a in audits),
                   matched_spans=sum(len(a['mask_spans']) for a in audits),
                   note='label-informed diagnostic; matches include guarded stems and dotted modules, not only full paths')
    write_json(directory/'leakage_summary.json',leakage)
    # Retain every paired rank change for inspectable examples; don't cherry-pick cohort.
    groups=_group(rows)
    examples=[]
    for (condition,method,instance), values in sorted(groups.items()):
        if method!='real':
            continue
        r=values[0]; b=groups[(condition,'bm25',instance)][0]
        gold=json.loads(r['gold_paths'])
        def first(row):
            return next((i+1 for i,p in enumerate(json.loads(row['predicted_paths'])) if p in gold),None)
        br, rr=first(b),first(r)
        if br!=rr:
            examples.append(dict(instance_id=instance,condition=condition,repo=r['repo'],base_commit=r['base_commit'],
                gold_paths=gold,bm25_rank=br,real_rank=rr,bm25_top10=json.loads(b['predicted_paths'])[:10],
                real_top10=json.loads(r['predicted_paths'])[:10]))
    write_json(directory/'rank_changes.json',examples)
    _plots(directory,rows,paired)
    print(markdown_table(summary))


def _plots(directory,rows,paired):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    figures=directory/'figures'; figures.mkdir(exist_ok=True)
    plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(1,2,figsize=(11,4),sharey=True)
    colors={'bm25':'#555555','real':'#006e90','rewired':'#d17a22','edge_drop':'#825ca6'}
    for ax,condition in zip(axes,['raw','masked']):
        for method in METHODS:
            subset=[r for r in rows if r['condition']==condition and r['method']==method]
            groups=defaultdict(list)
            for r in subset: groups[r['instance_id']].append(r)
            curve=[]
            for k in (1,3,5,10,20,50,100):
                curve.append(100*np.mean([np.mean([bool(set(json.loads(r['gold_paths'])) & set(json.loads(r['predicted_paths'])[:k])) for r in case]) for case in groups.values()]))
            ax.plot([1,3,5,10,20,50,100],curve,marker='o',label=method,color=colors[method])
        ax.set_xscale('log'); ax.set_xlabel('Returned file budget k (fixed candidate pool 100)')
        ax.set_title(condition); ax.grid(alpha=.2); ax.set_ylim(0,100)
    axes[0].set_ylabel('Hit@k (%)');axes[1].legend(frameon=False)
    fig.tight_layout();fig.savefig(figures/'accuracy_vs_budget.png',dpi=180);plt.close(fig)
    subset=[r for r in paired if r['metric']=='hit5' and r['control'] in ('bm25','rewired')]
    fig,ax=plt.subplots(figsize=(8,3.5))
    for i,r in enumerate(subset):
        ax.errorbar(r['difference_pp'],i,xerr=[[r['difference_pp']-r['lower_pp']],[r['upper_pp']-r['difference_pp']]],fmt='o',color='#006e90',capsize=4)
    ax.axvline(0,color='gray',linestyle='--');ax.set_yticks(range(len(subset)),[f"{r['condition']}: real − {r['control']}" for r in subset]);ax.set_xlabel('Hit@5 paired difference (percentage points), 95% bootstrap CI')
    fig.tight_layout();fig.savefig(figures/'paired_hit5.png',dpi=180);plt.close(fig)
