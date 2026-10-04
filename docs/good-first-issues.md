# Good first issues

Small, well-specified pieces of work for a first contribution. Each is self-contained, has a test to add, and needs no account, token or network access. Read [CONTRIBUTING.md](../CONTRIBUTING.md) first: standard library only, tests with every script, no network calls, plain language without em-dashes.

To claim one, open an issue with the title below (or comment on the existing one) and say you are working on it. Run `python3 -m pytest -q` and `python3 scripts/validate_plugins.py` before opening the pull request.

## 1. dead-code-finder: inventory CommonJS `module.exports`

**Labels:** good first issue, code-quality, python

**Context.** `plugins/code-quality/skills/dead-code-finder/scripts/dead_code_finder.py` lists ES module exports (`export function`, `export { a, b }`) as candidates but ignores CommonJS files, so `module.exports = { helper, other }` and `exports.helper = ...` never appear in the report.

**Acceptance criteria.**
- `js_candidates()` recognises `module.exports = { a, b: c }` (object literal keys), `module.exports.name =` and `exports.name =`, with the line number of each.
- A test in `tests/test_dead_code_finder.py` with one CommonJS file exporting two names, one of which is `require`d elsewhere; only the other is reported.
- The "Limits" section of `SKILL.md` drops the CommonJS sentence.

## 2. log-triage: `--since` and `--until` filters on parsed timestamps

**Labels:** good first issue, debugging, python

**Context.** `plugins/debugging/skills/log-triage/scripts/log_triage.py` normalises ISO 8601, Apache and syslog timestamps into `<ts>` but cannot restrict the window; users currently pre-filter with `--grep` on a date prefix, which only works for one format.

**Acceptance criteria.**
- `--since` and `--until` accept ISO 8601 values; a line is kept when the first timestamp in it (any of the three formats already recognised) falls in the window; lines without a timestamp follow the previous kept line's decision (so stack traces stay attached).
- Three tests: a window that keeps a subset, a window that keeps nothing (exit 0 with zero clusters), and a syslog-format line parsed with the current year.
- `SKILL.md` step 1 lists the new options.

## 3. cron-doctor: `--tz` for next-run computation

**Labels:** good first issue, devops, python

**Context.** `plugins/devops/skills/cron-doctor/scripts/cron_doctor.py` computes next runs in the time zone of `--now` (naive local time by default). Crontabs on servers usually run in UTC or under `CRON_TZ=`; the DST warning (CRON-011) also assumes a zone with transitions.

**Acceptance criteria.**
- `--tz Europe/London` (any `zoneinfo` key) sets the zone for `--now` when it is naive and for the next-run list; a `CRON_TZ=` line in the crontab takes precedence for the jobs below it.
- CRON-011 is skipped when the effective zone has no DST transitions (check two January and July offsets).
- Tests: a job at 02:30 across a DST change in a zone with transitions (next runs skip or repeat as cron would), and the same job under `--tz UTC` with no CRON-011.

## 4. csv-profiler: detect and report the quoting and line-ending dialect

**Labels:** good first issue, data, python

**Context.** `plugins/data/skills/csv-profiler/scripts/csv_profiler.py` sniffs the delimiter but reports nothing about quoting (`"` versus `'`), escaped quotes, `\r\n` versus `\n`, or a UTF-8 BOM, all of which break loaders.

**Acceptance criteria.**
- The report gains `dialect`: `quotechar`, `doublequote`, `line_terminator` (`CRLF`, `LF`, mixed) and `bom` (true or false), from `csv.Sniffer` plus a direct scan of the first 64 KB.
- A warning when line endings are mixed or a BOM is present.
- Tests with a CRLF file with a BOM and with a single-quoted file; the text output prints the dialect line.

## 5. changelog-keeper: `--format github` output for `show`

**Labels:** good first issue, docs, python

**Context.** `plugins/docs/skills/changelog-keeper/scripts/changelog.py show <version>` prints the Keep a Changelog section. GitHub release bodies and some chat tools want a flatter shape: categories as bold labels and entries as bullets, without the `##`/`###` headings, and with the compare link appended.

**Acceptance criteria.**
- `show --format github` prints `**Added**` style labels, bullets, and a final line `Full changelog: <compare link>` when the link reference exists.
- `--format` defaults to `keepachangelog` (current behaviour); `--json` is unchanged.
- Two tests: the GitHub format for a version with two categories and a link, and for one without links (no trailing line).

## 6. http-security-headers: HAR file input

**Labels:** good first issue, security-basics, python

**Context.** `plugins/security-basics/skills/http-security-headers/scripts/headers_check.py` reads a raw response or a JSON object of headers. Browsers export HAR files (`log.entries[].response.headers` as a list of `{name, value}`), which users currently have to convert by hand.

**Acceptance criteria.**
- A `.har` file (or JSON with a top-level `log.entries` array) is detected; `--url` selects the entry whose `request.url` matches (default: the first document response, `response.content.mimeType` starting with `text/html`, else the first entry).
- `status` in the report is `HTTP/<httpVersion> <status> <statusText>` from the entry.
- Tests: a minimal HAR with two entries where `--url` picks the second, and the default picks the HTML one; an entry list with duplicate `set-cookie` headers produces two cookie findings.
