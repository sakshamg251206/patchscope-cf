# Incomplete first pass — kept for transparency, not for reporting

This directory holds the first attempt at the full 300-issue run. It was stopped by hand
at case 181 of 300 and is marked incomplete, so `patchscope report` refuses to summarise
it. **Do not cite any number from this directory.**

## Why it was stopped

The snapshot fetcher used per-commit `git fetch --depth=1` with a 180-second timeout.
History-heavy repositories (matplotlib, astropy) regularly exceed that. When our timeout
killed a fetch, git left a `shallow.lock` file behind, and *every subsequent shallow
fetch in that repository* then failed with a bare exit status 128. Those cascading
failures produced seven **infrastructure** exclusions (six Django, one matplotlib).

They are not protocol exclusions — the issues are perfectly eligible — and reporting them
as ineligible cases would have been wrong.

## What was changed in response

1. `clear_stale_shallow_lock()` removes a stale lock before each fetch attempt
   (`patchscope/data.py`, regression test in `tests/test_data.py`).
2. The fetch timeout was raised to 1800 s and retries use exponential backoff.
3. A failed fetch now raises with the real git error text, so the exclusion reason is
   diagnosable instead of a bare exit status.
4. Each repository's full history is fetched once before the measured run
   (see the cold-cache tip in `README.md`).

No ranking method, cohort, seed, metric or parameter changed. The reported run is
`results/full300/`.
