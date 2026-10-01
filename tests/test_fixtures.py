import json
from pain_signal_detector.cli import load
from pain_signal_detector.fixtures import EXPECTED, generate
from pain_signal_detector.core import assess

def test_fixtures_labelled_synthetic(tmp_path):
    generate(tmp_path)
    for name in ('manifest.json', 'expectations.json'):
        assert json.loads((tmp_path / name).read_text())['synthetic'] is True
    assert (tmp_path / 'records.jsonl').read_text().startswith('# SYNTHETIC')
    assert (tmp_path / 'LABEL.md').read_text().startswith('<!-- SYNTHETIC -->')
    rows, _, _ = load(tmp_path)
    assert len(rows) == 200 and all(row['synthetic'] for row in rows)

def test_fixture_ground_truth_matches_hand_computed(tmp_path):
    generate(tmp_path)
    rows, day, _ = load(tmp_path)
    result = assess(rows, day)
    assert result['totals'] == {k: EXPECTED[k] for k in ('records', 'flagged', 'unflagged', 'by_rule')}
    assert [f['record']['id'] for f in result['findings']] == EXPECTED['flagged_ids']

def test_fixture_generation_deterministic(tmp_path):
    generate(tmp_path / 'a')
    generate(tmp_path / 'b')
    for path in (tmp_path / 'a').iterdir():
        assert path.read_bytes() == (tmp_path / 'b' / path.name).read_bytes()
