"""Local CLI. Inputs and results are explicit files, never network responses."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
from .core import InputError, RULES, assess, day, validate
from .fixtures import generate
from .report import banner, render

DEFAULT_RESULTS = ".psd/results.json"

def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise InputError(f"ParseError: {path}: line {exc.lineno}: {exc.msg}") from exc

def load(directory, as_of=None):
    root = Path(directory)
    if not root.is_dir():
        raise InputError(f"MissingInput: {root}: use psd fixtures --out demo or provide an existing input directory")
    manifest_path = root / "manifest.json"
    if not manifest_path.exists():
        if any(root.iterdir()):
            raise InputError(f"MissingInput: {manifest_path}: supply manifest.json; see psd run --help")
        if as_of is None:
            as_of = "2026-09-30"
        return [], as_of, []
    manifest = read_json(manifest_path)
    if not isinstance(manifest, dict):
        raise InputError(f"SchemaError: {manifest_path}: line 1: field manifest: expected object")
    extra = set(manifest) - {"schema_version", "as_of", "files", "synthetic", "label"}
    if extra:
        raise InputError(f"SchemaError: {manifest_path}: line 1: field {sorted(extra)[0]}: unknown field")
    if type(manifest.get("schema_version")) is not int or manifest["schema_version"] != 1:
        raise InputError(f"SchemaError: {manifest_path}: line 1: field schema_version: expected integer 1")
    if type(manifest.get("synthetic")) is not bool:
        raise InputError(f"SchemaError: {manifest_path}: line 1: field synthetic: expected boolean")
    as_of = as_of or manifest.get("as_of")
    try:
        day(as_of, "as_of")
    except InputError as exc:
        raise InputError(f"{exc}: {manifest_path}: line 1") from exc
    files = manifest.get("files")
    if not isinstance(files, list) or any(not isinstance(name, str) for name in files) or len(files) != len(set(files)):
        raise InputError(f"SchemaError: {manifest_path}: line 1: field files: expected distinct relative JSONL names")
    records, sources, seen = [], [], set()
    for name in sorted(files):
        path = root / name
        if "\u2014" in name or path.suffix != ".jsonl" or not path.resolve().is_relative_to(root.resolve()):
            raise InputError(f"SchemaError: {manifest_path}: line 1: field files: expected JSONL path within input directory")
        if not path.is_file():
            raise InputError(f"MissingInput: {path}: file listed in manifest is missing")
        sources.append(name)
        for line_no, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise InputError(f"ParseError: {path}: line {line_no}: {exc.msg}") from exc
            try:
                validate(row, as_of)
                if manifest["synthetic"] and not row["synthetic"]:
                    raise InputError("SchemaError: field synthetic: synthetic manifest cannot contain real records")
                if row["id"] in seen:
                    raise InputError(f"SchemaError: field id: duplicate id {row['id']!r}")
                seen.add(row["id"])
            except InputError as exc:
                raise InputError(f"{exc}: {path}: line {line_no}") from exc
            records.append(row)
    return records, as_of, sources

def atomic_write(path, text):
    path = Path(path)
    temporary = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(text)
        os.replace(temporary, path)
    except OSError as exc:
        raise InputError(f"WriteError: {path}: {exc.strerror or str(exc)}") from exc
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()

def parser():
    p = argparse.ArgumentParser(description="Assess supplied public evidence locally. No discovery or benefit estimates.")
    sub = p.add_subparsers(dest="command", required=True)
    f = sub.add_parser("fixtures", help="Generate 200 labelled synthetic records", epilog="Example: psd fixtures --out demo")
    f.add_argument("--out", required=True)
    for name, help_text in (("run", "Assess all supplied observations"), ("signals", "Filter computed signals by rule")):
        cmd = sub.add_parser(name, help=help_text, description=help_text, epilog=f"Example: psd {name} --input demo" + (" --rule server_error" if name == "signals" else ""))
        cmd.add_argument("--input", required=True, help="Directory with manifest.json and listed JSONL files")
        cmd.add_argument("--as-of", help="Explicit ISO assessment date; defaults to manifest date")
        if name == "run":
            cmd.add_argument("--results", default=DEFAULT_RESULTS)
        else:
            cmd.add_argument("--rule", choices=sorted(RULES), required=True)
    r = sub.add_parser("report", help="Render saved results with provenance", epilog="Example: psd report --format md")
    r.add_argument("--format", choices=("md", "json"), default="md")
    r.add_argument("--results", default=DEFAULT_RESULTS)
    r.add_argument("--out", help="Atomically write report to this path instead of stdout")
    e = sub.add_parser("explain", help="Explain each deterministic operational signal rule", epilog="Example: psd explain --rule overdue_issue")
    e.add_argument("--rule", choices=sorted(RULES))
    return p

def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "fixtures":
            generate(args.out)
            print(f"SYNTHETIC: generated 200 labelled records in {args.out}")
        elif args.command in ("run", "signals"):
            rows, as_of, sources = load(args.input, args.as_of)
            result = assess(rows, as_of)
            result["input_files"] = sources
            if args.command == "run":
                atomic_write(args.results, render(result, "json"))
                print(f"Computed {result['totals']['flagged']} signals from {len(rows)} supplied records. Results: {args.results}")
                print(banner(result))
                print(result["honesty"])
            else:
                result["selected_rule"] = args.rule
                result["selected_findings"] = [f for f in result["findings"] if f["rule"] == args.rule]
                print(render(result, "json"), end="")
        elif args.command == "explain":
            print("Rules assess supplied evidence only; hypothetical benefits are unmeasured.")
            for rule in sorted(RULES):
                if args.rule is None or rule == args.rule:
                    print(f"{rule}: {RULES[rule]}")
        else:
            path = Path(args.results)
            if not path.is_file():
                raise InputError(f"MissingInput: {path}: run psd run --input <dir> first")
            result = read_json(path)
            try:
                if not isinstance(result, dict):
                    raise ValueError("expected results object")
                computed = assess(result["records"], result["as_of"])
                extra = set(result) - (set(computed) | {"input_files", "banner"})
                if extra:
                    raise InputError(f"SchemaError: {path}: line 1: field {sorted(extra)[0]}: unknown field")
                if result.get("banner") != banner(computed):
                    raise InputError(f"SchemaError: {path}: line 1: field banner: provenance mismatch")
                for field, value in computed.items():
                    if result.get(field) != value:
                        raise InputError(f"SchemaError: {path}: line 1: field {field}: saved results do not reconcile; re-run inputs")
                if not isinstance(result.get("input_files"), list) or any(not isinstance(name, str) or "\u2014" in name for name in result["input_files"]):
                    raise ValueError("invalid input_files")
                output = render(result, args.format)
            except InputError:
                raise
            except (KeyError, TypeError, ValueError) as exc:
                raise InputError(f"SchemaError: {path}: line 1: field results: invalid saved results") from exc
            if args.out:
                atomic_write(args.out, output)
            else:
                print(output, end="")
        return 0
    except (InputError, OSError, UnicodeError) as exc:
        message = str(exc).replace("\u2014", "-")
        print(message if isinstance(exc, InputError) else f"InputReadError: {message}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    sys.exit(main())
