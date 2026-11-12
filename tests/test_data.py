import json
import subprocess

import pytest

from patchscope.labels import gold_paths, source_path
from patchscope.data import freeze_selection, snapshot


def test_labels_deleted_new_rename_windows_and_quoted():
    patch = '\n'.join(['+++ b/pkg/core.py', '+++ /dev/null',
                       '+++ b/tests/test_x.py', '+++ b/docs/conf.py',
                       '+++ b/pkg\\other.py', '+++ "b/pkg/with space.py"',
                       '+++ b/../evil.py', '+++ b/pkg/generated/x.py'])
    assert gold_paths(patch) == ['pkg/core.py', 'pkg/other.py', 'pkg/with space.py']
    assert not source_path('setup.py')
    assert not source_path('pkg/test_core.py')
    assert source_path('pkg/core.py')


def test_selection_frozen_before_labels(tmp_path):
    rows = [dict(instance_id=str(i), repo='a/b', base_commit='a'*40,
                 patch='secret', problem_statement='issue') for i in range(15)]
    path = tmp_path / 'manifest.json'
    chosen = freeze_selection(rows, 5, 2026, path, 'revision', 'test')
    assert len(chosen) == 5
    assert 'secret' not in path.read_text()
    assert freeze_selection(rows, 5, 2026, path, 'revision', 'test') == chosen
    with pytest.raises(ValueError, match='frozen'):
        freeze_selection(rows, 6, 2026, path, 'revision', 'test')
    assert len(json.loads(path.read_text())['instances']) == 5


def test_exact_git_snapshot_no_worktree_checkout(tmp_path):
    repo = tmp_path / 'repo'
    repo.mkdir()
    def git(*args):
        return subprocess.check_output(['git', '-C', str(repo), *args], text=True).strip()
    git('init', '-q')
    (repo / 'm.py').write_text('x = 1\n')
    git('add', '.')
    git('-c', 'user.name=Test', '-c', 'user.email=t@example.org', 'commit', '-qm', 'old')
    commit = git('rev-parse', 'HEAD')
    (repo / 'm.py').write_text('x = 2\n')
    git('add', '.')
    git('-c', 'user.name=Test', '-c', 'user.email=t@example.org', 'commit', '-qm', 'new')
    files, audit = snapshot('local/test', commit, tmp_path / 'cache', local_repo=repo)
    assert files == {'m.py': 'x = 1\n'}
    assert audit['commit'] == commit
    assert (repo / 'm.py').read_text() == 'x = 2\n'
    assert snapshot('local/test', commit, tmp_path / 'cache', local_repo=repo) == (files, audit)


def test_patch_hunk_content_is_not_a_file_header():
    patch = ('diff --git a/pkg/real.py b/pkg/real.py\n--- a/pkg/real.py\n'
             '+++ b/pkg/real.py\n@@ -1 +1,2 @@\n old\n+++ b/pkg/fake.py\n')
    assert gold_paths(patch) == ['pkg/real.py']
    assert not source_path('C:/outside.py')


def test_snapshot_rejects_modified_cached_contents(tmp_path):
    from patchscope.data import write_json
    commit = 'a'*40
    saved = tmp_path/'snapshots'/'a__b'/f'{commit}.json'
    write_json(saved, {'files': {'pkg/a.py':'future patch'},
                      'audit': {'commit':commit, 'repo':'a/b', 'source_sha256':'wrong'}})
    with pytest.raises(ValueError, match='checksum'):
        snapshot('a/b', commit, tmp_path)


def test_snapshot_rejects_unknown_cache_schema(tmp_path):
    import hashlib
    from patchscope.data import write_json
    commit='a'*40
    files={'x.py':'x=1'}
    saved=tmp_path/'snapshots'/'a__b'/f'{commit}.json'
    write_json(saved, {'files':files,'audit':{'repo':'a/b','commit':commit,
        'source_sha256':hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest(),
        'max_file_bytes':1,'max_files':1}})
    with pytest.raises(ValueError,match='limits'):
        snapshot('a/b',commit,tmp_path)


def test_stale_shallow_lock_is_cleared_so_fetches_are_not_poisoned(tmp_path):
    """A timed-out fetch leaves shallow.lock; later fetches then fail with status 128."""
    from patchscope.data import clear_stale_shallow_lock
    clone = tmp_path / 'repo.git'
    clone.mkdir()
    assert clear_stale_shallow_lock(clone) is False  # nothing to do on a clean repo
    lock = clone / 'shallow.lock'
    lock.write_text('')
    assert clear_stale_shallow_lock(clone) is True
    assert not lock.exists()
