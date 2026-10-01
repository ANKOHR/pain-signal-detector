# Local acceptance evidence

Measured on 2026-10-01 with Python 3.12.10 on Windows, CPU only.

Installed psd executable: fixture generation, run, and Markdown report write completed in 0.760957 seconds wall-clock. Threshold: under 5 seconds. This is measured execution time, not time saved. Input: 200 synthetic records, zero real records.

Observed totals: 200 records, 90 flagged, 110 unflagged. Rule totals: 40 server_error, 30 broken_contact, 20 overdue_issue. Independently planted IDs R001 through R090 match every finding exactly: zero fixture false positives and zero missed planted cases. This is fixture accuracy only, not a real-use accuracy claim.

pytest: 34 passed. Tests include the five-record hand-written example, malformed input with filename and line, empty input, duplicate IDs, dates, negative values, Unicode and long strings, repeated byte-identical outputs, failed report writes, and deliberate corruption of observations and saved totals.

No real trial has been performed. No measured savings, revenue, or demand is available. The two-week hook remains pending real use.
