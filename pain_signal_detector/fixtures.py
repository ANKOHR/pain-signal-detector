"""Synthetic fixtures. Fixed construction, no randomness or estimated figures."""
import json
from pathlib import Path

# Hand-computed oracle, independent of the engine: 40 + 30 + 20 = 90 signals.
EXPECTED = {
    "synthetic": True, "records": 200, "flagged": 90, "unflagged": 110,
    "by_rule": {"server_error": 40, "broken_contact": 30, "overdue_issue": 20},
    "flagged_ids": [f"R{i:03d}" for i in range(1, 91)],
}

def fixture_records():
    rows = []
    for i in range(1, 201):
        row = {"id": f"R{i:03d}", "synthetic": True, "observed_on": "2026-09-29",
               "source_url": f"https://example.invalid/observation/{i}", "evidence": "Synthetic planted observation"}
        if i <= 40 or i > 150:
            row.update(kind="website", http_status=503 if i <= 40 else 200)
        elif i <= 70 or i > 120:
            row.update(kind="contact", http_status=404 if i <= 70 else 200)
        else:
            row.update(kind="public_issue", status="open" if i <= 90 else "resolved", due_on="2026-09-01")
        rows.append(row)
    return rows

def generate(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    manifest = {"synthetic": True, "as_of": "2026-09-30", "schema_version": 1,
                "files": ["records.jsonl"], "label": "SYNTHETIC fixture, not real observations"}
    for name, obj in (("manifest.json", manifest), ("expectations.json", EXPECTED)):
        (out / name).write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = ["# SYNTHETIC fixture: every record is invented and labelled synthetic"]
    lines.extend(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in fixture_records())
    (out / "records.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (out / "LABEL.md").write_text("<!-- SYNTHETIC -->\nSynthetic fixture only. No real observations.\n", encoding="utf-8")
