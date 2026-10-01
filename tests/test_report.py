import json
from pain_signal_detector.core import assess
from pain_signal_detector.fixtures import EXPECTED, fixture_records
from pain_signal_detector.report import render

def test_report_matches_ground_truth_exact():
    result = json.loads(render(assess(fixture_records(), '2026-09-30'), 'json'))
    assert result['totals'] == {k: EXPECTED[k] for k in ('records', 'flagged', 'unflagged', 'by_rule')}

def test_report_zero_false_positives():
    result = json.loads(render(assess(fixture_records(), '2026-09-30'), 'json'))
    assert {f['record']['id'] for f in result['findings']} == set(EXPECTED['flagged_ids'])

def test_report_carries_provenance_banner():
    for format in ('md', 'json'):
        text = render(assess(fixture_records(), '2026-09-30'), format)
        assert 'SYNTHETIC fixtures: 200' in text
        assert 'REAL data manually entered by Henry: 0' in text

def test_hypothetical_figures_labelled():
    for format in ('md', 'json'):
        assert 'Hypothetical benefits are unmeasured and not quantified' in render(assess([], '2026-09-30'), format)

def test_no_em_dashes_in_outputs():
    for format in ('md', 'json'):
        assert '\u2014' not in render(assess(fixture_records(), '2026-09-30'), format)

def test_markdown_escapes_evidence():
    row = fixture_records()[0]
    row['evidence'] = '<script> | multi\nline'
    text = render(assess([row], '2026-09-30'))
    assert '&lt;script&gt; &#124; multi line' in text
