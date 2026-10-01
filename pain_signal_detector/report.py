"""Deterministic reports with explicit provenance and no invented benefits."""
import json

def banner(result):
    p = result["provenance"]
    return (f"Data provenance: SYNTHETIC fixtures: {p['synthetic_records']} records; "
            f"REAL data manually entered by Henry: {p['real_records_entered_by_Henry']} records. "
            "Provenance is declared by the input author, not independently verified.")

def safe(value):
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("|", "&#124;").replace("\n", " ").replace("\r", " ")

def render(result, format="md"):
    if format == "json":
        return json.dumps({"banner": banner(result), **result}, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if format != "md":
        raise ValueError("format must be md or json")
    totals = result["totals"]
    lines = ["# Pain Signal Detector", "", banner(result), "", f"Assessment date: {result['as_of']}", "",
             result["honesty"], "", f"Records: {totals['records']}", f"Flagged: {totals['flagged']}", f"Unflagged: {totals['unflagged']}", ""]
    lines.extend(f"{rule}: {count}" for rule, count in sorted(totals["by_rule"].items()))
    lines += ["", "## Evidence", "", "| ID | Rule | Observation | Source | Evidence | Provenance |", "| --- | --- | --- | --- | --- | --- |"]
    for finding in result["findings"]:
        row = finding["record"]
        lines.append("| " + " | ".join(safe(v) for v in (row["id"], finding["rule"], row["observed_on"], row["source_url"], row["evidence"], "synthetic" if row["synthetic"] else "real, entered by Henry")) + " |")
    return "\n".join(lines) + "\n"
