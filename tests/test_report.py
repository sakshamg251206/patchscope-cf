import json
import pytest
from patchscope.report import summarize, paired_comparisons


def fixture_rows():
    rows=[]
    for i in range(2):
        for method, seeds in [('bm25',[0]),('real',[0]),('rewired',[1,2,3]),('edge_drop',[1])]:
            for seed in seeds:
                value=float(method=='real' or i==0)
                rows.append(dict(instance_id=str(i), repo='a/b', condition='raw', method=method,seed=str(seed),
                    hit1=value,hit5=value,hit10=value,mrr10=value,recall5=value,recall10=value,query_ms=2.))
    return rows


def test_summary_counts_issues_not_rewiring_seeds():
    rows=fixture_rows()
    summary=summarize(rows)
    assert all(row['n']==2 for row in summary)
    real=next(row for row in summary if row['method']=='real')
    assert real['hit5']==1.
    comparison=next(row for row in paired_comparisons(rows) if row['control']=='rewired' and row['metric']=='hit5')
    assert comparison['difference_pp']==50.
    assert comparison['n']==2


def test_rejects_unpaired_or_incomplete_method_cohorts():
    rows=fixture_rows()
    with pytest.raises(ValueError,match='cohort'):
        summarize(rows[:-1])


def test_rejects_duplicate_control_seeds():
    rows = fixture_rows()
    for row in rows:
        if row['method']=='rewired':
            row['seed']='1'
    with pytest.raises(ValueError, match='seed'):
        summarize(rows)


def test_rejects_different_raw_masked_cohorts():
    rows = fixture_rows()
    rows += [{**row,'condition':'masked','instance_id':'other'} for row in fixture_rows() if row['instance_id']=='0']
    with pytest.raises(ValueError, match='cohort'):
        summarize(rows)
