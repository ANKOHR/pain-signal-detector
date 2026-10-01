# Pain Signal Detector

`psd` is a CPU-only Python CLI that flags explicit operational problems in supplied public observations. It makes no network calls and uses no models. Henry manually records public evidence; this tool applies reproducible rules to that evidence.

Hypothesis: deterministic rules can identify all planted operational problems with zero false positives on labelled fixtures. Acceptance: 200 records, exact reconciled counts, the full demo under five seconds, and all adversarial tests passing. Synthetic success tests implementation fidelity; it does not establish real-world targeting accuracy or buyer demand.

## Quickstart

Python 3.10 or later, setuptools 68 or later, and pytest for development are required. Runtime uses only the standard library. Installation can run entirely offline when setuptools is installed:

```powershell
python -m pip install --no-index --no-deps --no-build-isolation -e .
$env:Path += ";" + (python -c "import sysconfig; print(sysconfig.get_path('scripts', 'nt_user'))")
psd fixtures --out demo
psd run --input demo
psd report --format md
python -m pytest -q
```

The generated set has 200 synthetic records. The hand-computed expectation is 90 flagged and 110 unflagged: 40 server errors, 30 broken contact endpoints, and 20 overdue issues. These are planted cases, not real prospects. The independent oracle is in `expectations.json`; the engine never reads it. Altering a status in the records changes the report. A checked-in, hand-written five-record example is in `examples/tiny`. Run it with `psd run --input examples/tiny`.

## Input format

Only UTF-8 JSON and JSONL are accepted. CSV and YAML are deliberately unsupported; listing those files raises a named schema error. Each directory has a `manifest.json`:

```json
{"schema_version": 1, "as_of": "2026-09-30", "synthetic": false, "files": ["observations.jsonl"]}
```

`synthetic: false` allows real or mixed records; `true` requires every record to be synthetic. Paths must stay within the input directory, with no duplicate filenames. Only listed files are read. Ground truth files are never inputs. Dates are explicit rather than read from the machine clock. An empty directory yields zeros with the documented fallback assessment date 2026-09-30; `--as-of` can override it.

One JSON object per non-comment line in each JSONL file. Blank lines and lines beginning with `#` are ignored. Common fields:

| Field | Rule |
| --- | --- |
| `id` | Unique nonempty string, at most 20000 characters |
| `kind` | `website`, `contact`, or `public_issue` |
| `source_url` | HTTP(S) URL supplied by the author, without credentials |
| `observed_on` | ISO YYYY-MM-DD, no later than `as_of` |
| `evidence` | Nonempty observation text, at most 20000 characters |
| `synthetic` | Boolean, required on every record |
| `entered_by` | Required as `Henry` for real records; omitted for synthetic records |

Website and contact records require integer `http_status` from 100 through 599. Public issues require `status` (`open` or `resolved`) and ISO `due_on`. A future due date is valid and is not overdue. Unknown fields are rejected, including amounts and savings. Duplicate IDs, invalid dates, negative statuses, oversized strings, missing fields, and schema drift abort the entire run. No records are silently dropped. Unicode and Windows paths in evidence are supported. Em dash characters in record text are rejected with a named error to preserve the output constraint.

Illustrative synthetic input, not a measured observation:

```json
{"id":"demo-1","kind":"website","source_url":"https://example.invalid","observed_on":"2026-09-29","http_status":503,"evidence":"Synthetic HTTP response","synthetic":true}
```

Henry's real records use `synthetic: false` and `entered_by: "Henry"`. Keep real data and trial results outside the repository. Declaring provenance is an author assertion; the tool cannot verify authorship, whether a URL is publicly reachable, or whether an observation is true.

## Subcommands

| Command | Example and behavior |
| --- | --- |
| `fixtures` | `psd fixtures --out demo`: writes the labelled set and oracle; overwrites fixture filenames |
| `run` | `psd run --input demo --results .psd/results.json`: validates and assesses all records |
| `report` | `psd report --format json --out report.json`: renders saved results with provenance |
| `signals` | `psd signals --input demo --rule server_error`: shows selected findings alongside full-dataset totals |
| `explain` | `psd explain --rule overdue_issue`: describes the operational rule |

Every subcommand has `--help` and an example. The PATH line above applies only to the current PowerShell session and supports Python user installs on Windows. `run` and `signals` accept `--as-of YYYY-MM-DD`. Default results are `.psd/results.json` relative to the current directory; run and report from the same directory or pass `--results`. Reports are snapshots of the last successful run, not live views. Saved results include all validated observations so counts can be traced, and report rechecks their reconciliation before rendering. Re-run after editing inputs. No command computes accuracy without external ground truth.

Rules: a website status of 500 through 599 is `server_error`; a contact endpoint status of 400 through 599 is `broken_contact`; an open issue with `due_on` strictly before the assessment date is `overdue_issue`. A website 404 alone is not a server-error signal. Each record contributes at most one signal. Reports include source, date, evidence, ID, and provenance for every finding. Total records equals flagged plus unflagged; by-rule counts sum to flagged. A finding is evidence for review, not proof of an ongoing outage, an outreach opportunity, or a need to buy services.

## Architecture

```text
manifest.json + listed JSONL
            |
      cli.load: parse and validate
            |
      core.assess: pure deterministic rules
            |
      .psd/results.json: local snapshot
            |
      report.render: Markdown or JSON + provenance

fixtures.generate -> labelled synthetic files + independent oracle
pytest -> boundaries, adversarial inputs, reconciliation, demo
```

No randomness is used, so there is no seed. Stable ID sorting, rule sorting, JSON key sorting, explicit dates, UTF-8, and LF file output make repeated runs byte-identical for identical inputs and options. Runtime timing is recorded separately and is not placed in deterministic reports.

## Honesty boundary and fixture labelling

All counts are computed from supplied inputs. Nothing is discovered, predicted, or estimated. Synthetic JSON objects contain `synthetic: true`; JSONL has a synthetic header comment plus the field on every record; Markdown fixture labels contain an HTML header comment. JSON does not allow comments, so JSON fixture files carry the boolean field. Every report banner states synthetic counts and Henry-entered real counts, including empty reports. Hypothetical benefits are explicitly unmeasured and not quantified. No time saved or money saved is claimed: no measured baseline exists. Demo runtime is a measured execution time, not time saved.

## Failure modes

Malformed JSON gives `ParseError` with filename and line. Schema errors name the field, file, and record line. Missing input gives `MissingInput` with a usage hint and exit code 2. Invalid UTF-8 and filesystem read failures give `InputReadError`. Failed report writes give `WriteError`; temporary files are removed and an existing destination is preserved. Result writes are atomic. Fixture generation can leave already generated files if a later write fails; regenerate into a writable directory. A failed run does not overwrite the previous successful snapshot. The CLI never reads unlisted inputs. Saved result files are local generated artifacts and should not be manually edited.

## Two-week evidence hook and verdict

The real-use window starts on Henry's first recorded real run, not the build date. After fourteen days, hand-check all records if there are fewer than 50, otherwise a fixed sample of 50 including flagged and unflagged records. Record false positives and false negatives, sample size, `(FP + FN) / sample_size`, number of runs, and days used in a private trial log. This sampling metric is diagnostic, not a population estimate. If error exceeds 10 percent, fix the largest documented failure cause and repeat the check, or kill with a reason. If the tool is unused, kill with the reason recorded. Do not ship real trial data.

Record a dated verdict and evidence after that window: expand for daily use or revenue, integrate for heavy overlap with a sibling, commercialise for a buyer willing to pay as-is, maintain as portfolio evidence otherwise, or kill for non-use or unmet acceptance. `VERDICT.md` records the current provisional decision. Real-use evidence is not fabricated during the build.
