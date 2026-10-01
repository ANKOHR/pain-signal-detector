import json
import time
import pytest
from pain_signal_detector.cli import main
from pain_signal_detector.fixtures import generate

@pytest.fixture
def demo(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    generate('demo')
    return tmp_path

def test_run_completes_on_fixture(demo, capsys):
    start = time.perf_counter()
    assert main(['run', '--input', 'demo']) == 0
    assert main(['report', '--format', 'md']) == 0
    assert time.perf_counter() - start < 5
    assert 'Flagged: 90' in capsys.readouterr().out

def test_empty_input_renders_without_traceback(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / 'empty').mkdir()
    assert main(['run', '--input', 'empty']) == 0
    assert main(['report']) == 0
    assert 'Records: 0' in capsys.readouterr().out

def test_malformed_input_named_error(demo, capsys):
    (demo / 'demo/records.jsonl').write_text('# SYNTHETIC\n{broken\n')
    assert main(['run', '--input', 'demo']) == 2
    err = capsys.readouterr().err
    assert 'ParseError' in err and 'records.jsonl' in err and 'line 2' in err
    assert not (demo / '.psd/results.json').exists()

def test_determinism_byte_identical(demo):
    for output in ('a.json', 'b.json'):
        assert main(['run', '--input', 'demo', '--results', output]) == 0
    assert (demo / 'a.json').read_bytes() == (demo / 'b.json').read_bytes()
    for output in ('a.md', 'b.md'):
        assert main(['report', '--results', 'a.json', '--out', output]) == 0
    assert (demo / 'a.md').read_bytes() == (demo / 'b.md').read_bytes()

def test_cli_smoke_all_subcommands(demo, capsys):
    commands = [['fixtures', '--out', 'another'], ['run', '--input', 'demo'],
                ['report', '--format', 'json'], ['signals', '--input', 'demo', '--rule', 'server_error'], ['explain', '--rule', 'overdue_issue']]
    for command in commands:
        assert main(command) == 0
    for command in ('fixtures', 'run', 'report', 'signals', 'explain'):
        with pytest.raises(SystemExit) as exc:
            main([command, '--help'])
        assert exc.value.code == 0
    assert '\u2014' not in capsys.readouterr().out

def test_missing_input_named_error(demo, capsys):
    assert main(['run', '--input', 'missing']) == 2
    assert 'MissingInput' in capsys.readouterr().err

def test_report_write_failure_no_partial_files(demo, capsys):
    assert main(['run', '--input', 'demo']) == 0
    (demo / 'blocked').mkdir()
    before = set(demo.iterdir())
    assert main(['report', '--out', 'blocked']) == 2
    assert 'WriteError' in capsys.readouterr().err
    assert set(demo.iterdir()) == before

def test_schema_error_names_field_and_line(demo, capsys):
    (demo / 'demo/records.jsonl').write_text(json.dumps({'synthetic': True}) + '\n')
    assert main(['run', '--input', 'demo']) == 2
    error = capsys.readouterr().err
    assert 'SchemaError' in error and 'field' in error and 'line 1' in error

def test_manifest_path_escape_rejected(demo, capsys):
    path = demo / 'demo/manifest.json'
    manifest = json.loads(path.read_text())
    manifest['files'] = ['../outside.jsonl']
    path.write_text(json.dumps(manifest))
    assert main(['run', '--input', 'demo']) == 2
    assert 'field files' in capsys.readouterr().err

def test_saved_results_corruption_rejected(demo, capsys):
    assert main(['run', '--input', 'demo']) == 0
    path = demo / '.psd/results.json'
    result = json.loads(path.read_text())
    result['totals']['flagged'] = 999
    path.write_text(json.dumps(result))
    assert main(['report', '--format', 'json']) == 2
    assert 'field totals' in capsys.readouterr().err

def test_tiny_hand_written_input(tmp_path):
    from pathlib import Path
    from pain_signal_detector.cli import load
    from pain_signal_detector.core import assess
    root = Path(__file__).resolve().parents[1] / 'examples/tiny'
    rows, day, _ = load(root)
    expected = json.loads((root / 'expectations.json').read_text())
    assert assess(rows, day)['totals'] == {key: expected[key] for key in ('records', 'flagged', 'unflagged', 'by_rule')}
