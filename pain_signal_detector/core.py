"""Pure validation and rules. No network, I/O, predictions, or savings estimates."""
from datetime import date
from urllib.parse import urlsplit

KINDS = ("website", "contact", "public_issue")
RULES = {
    "server_error": "Supplied website HTTP status is 500 through 599.",
    "broken_contact": "Supplied contact endpoint HTTP status is 400 through 599.",
    "overdue_issue": "Supplied public issue is unresolved and due before the assessment date.",
}

class InputError(ValueError):
    """A named input failure suitable for CLI display."""

def fail(field, message):
    raise InputError(f"SchemaError: field {field}: {message}")

def day(value, field):
    if not isinstance(value, str):
        fail(field, "expected ISO date YYYY-MM-DD")
    try:
        result = date.fromisoformat(value)
    except ValueError:
        fail(field, "expected ISO date YYYY-MM-DD")
    if result.isoformat() != value:
        fail(field, "expected ISO date YYYY-MM-DD")
    return result

def validate(record, as_of):
    if not isinstance(record, dict):
        fail("record", "expected object")
    common = {"id", "kind", "source_url", "observed_on", "evidence", "synthetic"}
    missing = common - record.keys()
    if missing:
        fail(sorted(missing)[0], "required")
    kind = record["kind"]
    if not isinstance(kind, str) or kind not in KINDS:
        fail("kind", "expected website, contact, or public_issue")
    allowed = common | {"entered_by"} | ({"status", "due_on"} if kind == "public_issue" else {"http_status"})
    extra = record.keys() - allowed
    if extra:
        fail(sorted(extra)[0], "unknown field (schema drift)")
    for field in ("id", "source_url", "evidence"):
        value = record[field]
        if not isinstance(value, str) or not value.strip() or len(value) > 20000:
            fail(field, "expected nonempty string of at most 20000 characters")
        if "\u2014" in value:
            fail(field, "em dash is unsupported; use a hyphen")
    try:
        url = urlsplit(record["source_url"])
        if url.scheme not in ("http", "https") or not url.hostname or url.username or url.password:
            fail("source_url", "expected public HTTP(S) evidence URL without credentials")
    except ValueError:
        fail("source_url", "invalid URL")
    if type(record["synthetic"]) is not bool:
        fail("synthetic", "expected boolean")
    if not record["synthetic"] and record.get("entered_by") != "Henry":
        fail("entered_by", "real observations require Henry's own manual entry: Henry")
    if record["synthetic"] and "entered_by" in record:
        fail("entered_by", "omit for synthetic records")
    if day(record["observed_on"], "observed_on") > day(as_of, "as_of"):
        fail("observed_on", "future observation relative to as_of")
    if kind == "public_issue":
        if record.get("status") not in ("open", "resolved"):
            fail("status", "expected open or resolved")
        if "due_on" not in record:
            fail("due_on", "required")
        day(record["due_on"], "due_on")
    else:
        value = record.get("http_status")
        if type(value) is not int or not 100 <= value <= 599:
            fail("http_status", "expected integer 100 through 599")
    return record

def signal(record, as_of):
    if record["kind"] == "website" and record["http_status"] >= 500:
        return "server_error"
    if record["kind"] == "contact" and record["http_status"] >= 400:
        return "broken_contact"
    if record["kind"] == "public_issue" and record["status"] == "open" and record["due_on"] < as_of:
        return "overdue_issue"
    return None

def assess(records, as_of):
    day(as_of, "as_of")
    validated, seen = [], set()
    for record in records:
        validate(record, as_of)
        if record["id"] in seen:
            fail("id", f"duplicate id {record['id']!r}")
        seen.add(record["id"])
        validated.append(record)
    validated.sort(key=lambda row: row["id"])
    findings = []
    counts = dict.fromkeys(RULES, 0)
    for record in validated:
        rule = signal(record, as_of)
        if rule:
            counts[rule] += 1
            findings.append({"rule": rule, "record": record})
    synthetic = sum(row["synthetic"] for row in validated)
    return {
        "schema_version": 1, "as_of": as_of,
        "provenance": {"synthetic_records": synthetic, "real_records_entered_by_Henry": len(validated) - synthetic},
        "totals": {"records": len(validated), "flagged": len(findings), "unflagged": len(validated) - len(findings), "by_rule": counts},
        "findings": findings,
        "records": validated,
        "honesty": "Counts computed only from supplied observations. No demand, accuracy, time saved, or money saved measured. Hypothetical benefits are unmeasured and not quantified.",
    }
