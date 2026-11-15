"""Exercise the patched owner GUI offscreen, with no engine or game data."""
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


PROJECT = Path(__file__).resolve().parents[1]
STORE = Path.home() / '.local/share/eql-automation'


def test_gfay_preview_destination_selection_dialogs_and_crossing_badge(tmp_path):
    source = STORE / 'owner-assist/0.39.13'
    ui_python = STORE / 'python-ui/bin/python'
    if not source.is_dir() or not ui_python.is_file():
        pytest.skip('Pinned retained preview and isolated Qt environment unavailable')
    draft = tmp_path / 'preview'
    subprocess.run([
        sys.executable, str(PROJECT / 'tools/build_nov12_preview_03942.py'),
        '--source', str(source), '--output', str(draft),
    ], cwd=PROJECT, check=True, capture_output=True, text=True)
    report = tmp_path / 'gui.json'
    code = r'''
import json
from pathlib import Path
import sys
import traceback

draft, report = map(Path, sys.argv[1:])
sys.path.insert(0, str(draft))
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QCheckBox, QDialog, QLabel
import owner_nov12_entry
owner_nov12_entry.verify_snapshot(draft)
import rotation_engine
from rotation_core import Catalog, Settings
import leveling_guide
import eql_rotation
from eql_automation.source_destinations import DESTINATIONS, destination_spec

def forbidden(*args, **kwargs):
    raise AssertionError('GUI-only test must not create an engine or save settings')
rotation_engine.Engine = forbidden
Settings.save = forbidden
leveling_guide.default_guide = lambda: None
app = QApplication.instance() or QApplication([])
results, errors = [], []
new_ids = (
    'butcher-gfay-preline-stop', 'butcher-gfay-crossing',
    'gfay-orc-camps', 'gfay-orc-camps-stop',
    'gfay-crushbone-preline-stop', 'gfay-crushbone-crossing',
    'gfay-butcher-crushbone-preline-stop', 'gfay-butcher-crushbone-crossing',
)

def exercise():
    try:
        window = next(w for w in app.topLevelWidgets() if hasattr(w, 'source_destination'))
        assert window.worker is None
        box = window.source_destination
        identifiers = [box.itemData(i) for i in range(box.count())]
        assert len(identifiers) == len(set(identifiers)) == 16
        assert set(identifiers) == set(DESTINATIONS)
        posts, dialogs = [], []
        window.post = lambda *args: posts.append(args)

        def accept(dialog):
            labels = [label.text() for label in dialog.findChildren(QLabel)]
            dialogs.append((dialog.windowTitle(), '\n'.join(labels)))
            confirmation = next(c for c in dialog.findChildren(QCheckBox)
                                if c.text().startswith('I will supervise'))
            confirmation.setChecked(True)
            return QDialog.DialogCode.Accepted
        QDialog.exec = accept

        for identifier in new_ids:
            # Start from a checked camp option to expose stale continuation.
            box.setCurrentIndex(box.findData('slave-mines'))
            window.continue_camps.setChecked(True)
            box.setCurrentIndex(box.findData(identifier))
            mode = destination_spec(identifier).arrival_mode
            is_camp = mode == 'camp'
            assert window.continue_camps.isEnabled() == is_camp
            assert window.continue_camps.isChecked() == is_camp
            help_text = window.travel_help.text()
            assert help_text == eql_rotation.gfay_destination_help(identifier)
            if mode == 'zone_crossing':
                assert 'two fresh location replies' in help_text
                assert 'starts no camp' in help_text
                assert 'does not continue to another zone' in help_text
            elif is_camp:
                assert 'levels 4–7' in help_text
                assert 'no supported onward camp' in help_text
            elif 'preline' in identifier:
                assert 'without crossing or combat' in help_text
            # Even a programmatically stale disabled checkbox cannot post true.
            window.continue_camps.setChecked(True)
            window.configure_supervised_source()
            job, declaration = posts[-1]
            assert job == 'supervised_crushbone_source_travel'
            assert declaration == dict(open_flat_clear=True, destination_id=identifier,
                                       continue_camps=is_camp)
            title, description = dialogs[-1]
            assert title.endswith(', then camp' if is_camp else ', then stop')
            assert help_text in description
            QDialog.exec = lambda self: QDialog.DialogCode.Rejected
            count = len(posts)
            window.configure_supervised_source()
            assert len(posts) == count
            QDialog.exec = accept
            results.append(dict(destination_id=identifier, arrival_mode=mode,
                                posted_continue_camps=is_camp, help=help_text))

        for phase in ('source_crossing_handoff', 'source_crossing'):
            window.render_autopilot(dict(state='running', journey_phase=phase,
                journey_destination_id='gfay-crushbone-crossing'))
            assert 'TRAVEL TEST RUNNING' in window.ap_state.text()
            assert 'Clan Crushbone' in window.ap_state.text()
            assert not box.isEnabled() and not window.continue_camps.isEnabled()
        window.render_autopilot(dict(state='off'))
        assert box.isEnabled()
        assert window.worker is None
        report.with_suffix('.checks.json').write_text(json.dumps(dict(destinations=results, checks=8,
            worker_started=False, game_input_sent=False, settings_saved=False), indent=2))
    except BaseException:
        errors.append(traceback.format_exc())
        app.quit()

QTimer.singleShot(0, exercise)
eql_rotation.run_gui(Settings(game_dir=str(report.parent / 'empty-client')),
                     Catalog([]), smoke_path=report.with_suffix('.png'), smoke_view=(3, 0))
if errors:
    raise AssertionError('\n'.join(errors))
assert len(results) == 8
'''
    env = dict(os.environ, QT_QPA_PLATFORM='offscreen', PYTHONDONTWRITEBYTECODE='1')
    result = subprocess.run([str(ui_python), '-c', code, str(draft), str(report)],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    # Retain both the exercised controls and the normal GUI smoke observation.
    checks = json.loads(report.with_suffix('.checks.json').read_text())
    assert checks['checks'] == 8 and len(checks['destinations']) == 8
    observed = json.loads(report.read_text())
    assert not observed['worker_started'] and not observed['game_input_sent']
    assert not observed['settings_saved']
    assert len(observed['journey_destination_ids']) == 16
    assert report.with_suffix('.png').is_file()
    for name in ('rotation_core.py', 'launch.sh'):
        assert sha256((draft / name).read_bytes()).digest() == sha256((source / name).read_bytes()).digest()
    # Existing camp patches already change the older 0.39.13 engine. Preserve
    # the retained 0.39.41 engine, rather than comparing to that earlier input.
    assert sha256((draft / 'rotation_engine.py').read_bytes()).hexdigest() == (
        'd4925d8250e69d6e631f64b4c7eea115b34473aef90d86c9838c045ad355309e')
