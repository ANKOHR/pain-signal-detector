import pytest
from pain_signal_detector.core import InputError, assess
from pain_signal_detector.fixtures import fixture_records

@pytest.mark.parametrize('patch', [
    {'http_status': -1}, {'http_status': True}, {'observed_on': '2027-01-01'},
    {'kind': []}, {'evidence': 'x' * 20001}, {'amount': -1},
    {'synthetic': 'true'}, {'source_url': 'file:///C:/secret'},
    {'observed_on': '20260929'}, {'evidence': ''},
])
def test_rejects_adversarial_values(patch):
    row = fixture_records()[0]
    row.update(patch)
    with pytest.raises(InputError, match='SchemaError: field'):
        assess([row], '2026-09-30')

def test_duplicate_ids():
    row = fixture_records()[0]
    with pytest.raises(InputError, match='duplicate id'):
        assess([row, row], '2026-09-30')

def test_handles_unicode_and_long_inputs():
    row = fixture_records()[0]
    row['evidence'] = '患者 café 🚀 C:\\Users\\Henry ' + 'z' * 19000
    assert assess([row], '2026-09-30')['findings'][0]['record'] == row

def test_boundary_rules_and_real_provenance():
    rows = fixture_records()[:5]
    for row, code in zip(rows, (499, 500, 599, 200, 400)):
        row.update(http_status=code, synthetic=False, entered_by='Henry')
    result = assess(rows, '2026-09-30')
    assert result['totals']['flagged'] == 2
    assert result['provenance']['real_records_entered_by_Henry'] == 5
    issue = fixture_records()[70]
    for due in ('2026-09-30', '2026-10-01'):
        issue['due_on'] = due
        assert assess([issue], '2026-09-30')['totals']['flagged'] == 0

def test_ground_truth_corruption_changes_output():
    rows = fixture_records()
    before = assess(rows, '2026-09-30')
    rows[0]['http_status'] = 200
    after = assess(rows, '2026-09-30')
    assert after['totals']['flagged'] == before['totals']['flagged'] - 1
