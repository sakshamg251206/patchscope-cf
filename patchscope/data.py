"""Pinned metadata and read-only git-object snapshots; never apply patches."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
import re
import subprocess
import ssl
import certifi
import time
from urllib.request import Request, urlopen

DATASET = 'SWE-bench/SWE-bench_Lite'
DATASET_REVISION = 'b0dde1093fe417d83b7184254edf8199c1f0dff5'
MAX_FILE_BYTES = 250_000
MAX_FILES = 20_000


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
    temporary.replace(path)


def download(url: str, path: Path):
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers={'User-Agent': 'PatchScope-CF/0.1'}), timeout=60, context=ssl.create_default_context(cafile=certifi.where())) as response:
                payload = response.read()
            temp = path.with_suffix(path.suffix + '.tmp')
            temp.write_bytes(payload)
            temp.replace(path)
            return
        except (OSError, TimeoutError):
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def fetch_dataset(cache: Path, split='test') -> tuple[list[dict], str]:
    import pyarrow.parquet as pq
    if split not in {'dev', 'test'}:
        raise ValueError('split must be dev or test')
    info = cache / 'dataset_info.json'
    download(f'https://huggingface.co/api/datasets/{DATASET}', info)
    revision = DATASET_REVISION
    parquet = cache / f'{revision}-{split}.parquet'
    download(f'https://huggingface.co/datasets/{DATASET}/resolve/{revision}/data/{split}-00000-of-00001.parquet', parquet)
    return pq.read_table(parquet).to_pylist(), revision


def freeze_selection(rows, sample: int, seed: int, path: Path, revision: str, split: str):
    if sample < 1 or sample > len(rows):
        raise ValueError(f'sample must be between 1 and {len(rows)}')
    ordered = sorted(rows, key=lambda row: row['instance_id'])
    random.Random(seed).shuffle(ordered)
    selected = ordered[:sample]
    identity = dict(seed=seed, split=split, requested=sample, revision=revision,
                    selection='sorted IDs then Python Random(seed).shuffle; first N; no replacements',
                    instances=[{k: row[k] for k in ('instance_id', 'repo', 'base_commit')} for row in selected])
    if path.exists():
        previous = json.loads(path.read_text())
        for key, value in identity.items():
            if previous.get(key) != value:
                raise ValueError(f'frozen selection differs at {key}; use a new output directory')
    else:
        write_json(path, {**identity, 'frozen_at_utc': datetime.now(timezone.utc).isoformat()})
    return selected


def clear_stale_shallow_lock(clone: Path) -> bool:
    """Remove a `shallow.lock` left behind by a fetch that was killed by a timeout.

    Without this, every later shallow fetch in that repository fails with a bare exit
    status 128, which an evaluation run would otherwise record as case exclusions.
    Fetches are serialised within a run, so a lock seen here is never live.
    """
    stale = clone / 'shallow.lock'
    if stale.exists():
        stale.unlink()
        return True
    return False


def _git(repo: Path, *args, timeout=180) -> bytes:
    return subprocess.check_output(['git', '-C', str(repo), *args], timeout=timeout, stderr=subprocess.PIPE)


def snapshot(repo: str, commit: str, cache: Path, local_repo: Path | None = None):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo):
        raise ValueError('invalid repository name')
    if not re.fullmatch(r'[a-f0-9]{40}', commit):
        raise ValueError('base_commit must be a full hexadecimal SHA')
    saved = cache / 'snapshots' / repo.replace('/', '__') / f'{commit}.json'
    if saved.exists():
        record = json.loads(saved.read_text())
        if record['audit']['commit'] != commit or record['audit'].get('repo') != repo:
            raise ValueError('snapshot cache identity mismatch')
        digest = hashlib.sha256(json.dumps(record['files'], sort_keys=True).encode()).hexdigest()
        if digest != record['audit'].get('source_sha256'):
            raise ValueError('snapshot cache source checksum mismatch')
        if (record['audit'].get('max_file_bytes') != MAX_FILE_BYTES
                or record['audit'].get('max_files') != MAX_FILES):
            raise ValueError('snapshot cache limits differ from current protocol')
        return record['files'], record['audit']
    clone = local_repo or cache / 'repos' / repo.replace('/', '__')
    if local_repo is None:
        if not clone.exists():
            clone.mkdir(parents=True)
            _git(clone, 'init', '--bare', '-q')
            _git(clone, 'remote', 'add', 'origin', f'https://github.com/{repo}.git')
        try:
            _git(clone, 'cat-file', '-e', commit + '^{commit}')
        except subprocess.CalledProcessError:
            # Long runs fetch hundreds of commits; transient remote failures must not be
            # mistaken for protocol exclusions, so back off further and report the real
            # git error rather than a bare exit status.
            attempts = 5
            for attempt in range(attempts):
                clear_stale_shallow_lock(clone)
                try:
                    # Shallow packs for history-heavy repositories (matplotlib, astropy)
                    # routinely take minutes; a short timeout turns a slow download into
                    # a spurious exclusion.
                    _git(clone, 'fetch', '--depth=1', '--no-tags', 'origin', commit, timeout=1800)
                    break
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
                    if attempt == attempts - 1:
                        detail = getattr(exc, 'stderr', b'') or b''
                        raise ValueError(
                            f'git fetch failed for {repo}@{commit} after {attempts} attempts: '
                            + detail.decode('utf-8', 'replace').strip().replace('\n', ' ')[:400]) from exc
                    time.sleep(2 ** attempt)
    resolved = _git(clone, 'rev-parse', commit + '^{commit}').decode().strip()
    assert resolved == commit
    tree = _git(clone, 'ls-tree', '-r', '-z', '--long', commit)
    from .labels import source_path
    blobs, skipped = [], []
    for entry in tree.split(b'\0'):
        if not entry:
            continue
        metadata, raw_path = entry.split(b'\t', 1)
        mode, kind, oid, size = metadata.split()
        path = raw_path.decode('utf-8', errors='surrogateescape')
        if kind != b'blob' or not source_path(path):
            continue
        if mode == b'120000' or int(size) > MAX_FILE_BYTES:
            skipped.append({'path': path, 'reason': 'symlink_or_oversize'})
            continue
        blobs.append((path, oid.decode()))
    if len(blobs) > MAX_FILES:
        raise ValueError(f'eligible file cap exceeded: {len(blobs)} > {MAX_FILES}')
    # One process avoids thousands of git invocations; bytes are never executed.
    result = subprocess.run(['git', '-C', str(clone), 'cat-file', '--batch'],
                            input=('\n'.join(oid for _, oid in blobs) + '\n').encode(),
                            capture_output=True, check=True, timeout=180)
    data, offset, files = result.stdout, 0, {}
    for path, oid in blobs:
        end = data.index(b'\n', offset)
        header = data[offset:end].split()
        assert header[0].decode() == oid and header[1] == b'blob'
        length = int(header[2])
        raw = data[end + 1:end + 1 + length]
        offset = end + length + 2
        # Python source encoding declarations matter in historical snapshots.
        import io
        import tokenize
        try:
            encoding, _ = tokenize.detect_encoding(io.BytesIO(raw).readline)
            files[path] = raw.decode(encoding)
        except (UnicodeError, SyntaxError, LookupError):
            skipped.append({'path': path, 'reason': 'decode_error'})
    audit = dict(repo=repo, commit=commit, num_files=len(files), skipped=skipped,
                 max_file_bytes=MAX_FILE_BYTES, max_files=MAX_FILES,
                 tree_sha256=hashlib.sha256(tree).hexdigest(),
                 source_sha256=hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest())
    write_json(saved, dict(files=files, audit=audit))
    return files, audit
