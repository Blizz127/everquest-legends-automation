"""Build and exercise the local itinerary preview offscreen without an engine."""
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


PROJECT = Path(__file__).resolve().parents[1]
STORE = Path.home() / '.local/share/eql-automation'


def test_itinerary_preview_declarations_progress_stop_controls_and_entry_wiring(tmp_path):
    source = STORE / 'owner-assist/0.39.13'
    ui_python = STORE / 'python-ui/bin/python'
    if not source.is_dir() or not ui_python.is_file():
        pytest.skip('Pinned retained preview and isolated Qt environment unavailable')
    draft = tmp_path / 'preview'
    subprocess.run([
        sys.executable, str(PROJECT / 'tools/build_nov12_preview_03943.py'),
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
from PySide6.QtWidgets import QApplication, QCheckBox, QDialog, QDialogButtonBox, QLabel, QPushButton
import owner_nov12_entry
owner_nov12_entry.verify_snapshot(draft)
import rotation_engine
from rotation_core import Catalog, Settings
import leveling_guide
import eql_rotation
import eql_automation.owner_journey_runtime as journey_module
import eql_automation.owner_zone_itinerary_assets as plan_module
from eql_automation.source_destinations import DESTINATIONS, destination_spec

def forbidden(*args, **kwargs):
    raise AssertionError('GUI-only test must not create an engine, load a trip or save settings')
rotation_engine.Engine = forbidden
Settings.save = forbidden
leveling_guide.default_guide = lambda: None
# Exercise the actual built entry after verifying its full source snapshot.
# Its engine factory is captured, and the application entry is a no-op.
wiring, launched = [], []
actual_factory, actual_main = journey_module.make_owner_journey_engine, eql_rotation.main
actual_provider = plan_module.load_owner_zone_itinerary
def capture_factory(base, **kwargs):
    wiring.append((base, kwargs))
    return forbidden
journey_module.make_owner_journey_engine = capture_factory
eql_rotation.main = lambda: launched.append(True)
saved_argv = sys.argv
try:
    sys.argv = [str(draft / 'owner_nov12_entry.py')]
    assert owner_nov12_entry.main() == 0
finally:
    sys.argv = saved_argv
    journey_module.make_owner_journey_engine = actual_factory
    eql_rotation.main = actual_main
assert len(wiring) == 1 and wiring[0][0] is forbidden
assert wiring[0][1]['zone_itinerary_provider'] is actual_provider
assert launched == [True]
# The GUI must use profile metadata only, never call a plan/asset loader.
plan_module.load_owner_zone_itinerary = forbidden
app = QApplication.instance() or QApplication([])
checks, errors = [], []
# Dialog painting may process Qt events. Defer the inherited smoke timer until
# all checks finish so a slow host cannot capture/quit midway through a dialog.
actual_single_shot = QTimer.singleShot
smoke_render = []
def schedule(milliseconds, callback):
    if milliseconds == 400:
        smoke_render.append(callback)
    else:
        actual_single_shot(milliseconds, callback)
QTimer.singleShot = schedule

def exercise():
    try:
        window = next(w for w in app.topLevelWidgets() if hasattr(w, 'zone_itinerary_start'))
        assert window.worker is None
        button = window.zone_itinerary_start
        assert button.objectName() == 'zoneItineraryButton' and button.isEnabled()
        assert 'Butcherblock' in button.text() and 'Clan Crushbone' in button.text()
        help_text = window.zone_itinerary_help.text()
        assert help_text == eql_rotation.owner_itinerary_help()
        assert '5 hours 28 minutes' in help_text
        assert 'maximum limit, not a travel-time estimate' in help_text
        assert 'then stop without combat or a camp' in help_text
        assert 'F8' in help_text and 'F9/F11' in help_text
        posts = []
        dialog_images = set()
        window.post = lambda *args: posts.append(args)
        # A stale unrelated camp option must not leak into the itinerary job.
        window.source_destination.setCurrentIndex(window.source_destination.findData('slave-mines'))
        window.continue_camps.setChecked(True)

        def dialog_result(ground_value, supervision_value, accepted=True, become_busy=False):
            def finish(dialog):
                assert dialog.objectName() == 'zoneItineraryDialog'
                assert dialog.windowTitle() == 'Butcherblock → Greater Faydark → Clan Crushbone, then stop'
                labels = '\n'.join(v.text() for v in dialog.findChildren(QLabel))
                assert help_text in labels and '/location' in labels
                ground = dialog.findChild(QCheckBox, 'itineraryGroundDeclaration')
                supervision = dialog.findChild(QCheckBox, 'itinerarySupervisionDeclaration')
                buttons = dialog.findChild(QDialogButtonBox)
                ok = buttons.button(QDialogButtonBox.StandardButton.Ok)
                assert not ground.isChecked() and not supervision.isChecked() and not ok.isEnabled()
                ground.setChecked(ground_value)
                assert not ok.isEnabled()
                supervision.setChecked(supervision_value)
                assert ok.isEnabled() == (ground_value and supervision_value)
                image_kind = 'ready' if ground_value and supervision_value else 'disabled'
                if image_kind not in dialog_images:
                    dialog.ensurePolished()
                    dialog.adjustSize()
                    dialog.show()
                    app.processEvents()
                    screenshot = dialog.grab()
                    assert screenshot.width() >= 600 and screenshot.height() >= 250
                    assert screenshot.save(str(report.with_suffix('.dialog-'+image_kind+'.png')))
                    dialog.hide()
                    dialog_images.add(image_kind)
                if become_busy:
                    window.render_autopilot(dict(state='running', journey_phase='travel'))
                return QDialog.DialogCode.Accepted if accepted else QDialog.DialogCode.Rejected
            return finish

        for ground, supervision, accepted in ((False, False, True), (True, False, True),
                                              (False, True, True), (True, True, False)):
            QDialog.exec = dialog_result(ground, supervision, accepted)
            before = len(posts)
            window.configure_zone_itinerary()
            assert len(posts) == before
            checks.append('declaration-refusal')
        QDialog.exec = dialog_result(True, True)
        button.click()
        assert posts[-1] == ('zone_itinerary', dict(itinerary_id='butcher-gfay-crushbone',
            open_flat_clear=True, owner_supervised_continuation=True))
        checks.append('exact-itinerary-request')
        QDialog.exec = dialog_result(True, True, become_busy=True)
        before = len(posts)
        window.configure_zone_itinerary()
        assert len(posts) == before and not button.isEnabled()
        # A direct stale GUI callback is also inert while another trip owns it.
        QDialog.exec = forbidden
        window.configure_zone_itinerary()
        assert len(posts) == before
        checks.append('busy-dialog-refusal')

        def update(payload, *, active=False, preparing=False):
            window.update_state(dict(status='Synthetic GUI state', active=active, preparing=preparing,
                known=None, prepared=False, level=window.settings.level, profile={}, hp=None, mana=None,
                stance_keys_verified=False, autopilot=payload))

        for journey_phase, leg, stage, label in (
            ('setup', 1, 'walking', 'Travel'),
            ('source_crossing', 1, 'crossing', 'Crossing'),
            ('source_crossing', 1, 'loading', 'Loading zone'),
            ('source_crossing', 1, 'arrival', 'Checking arrival'),
            ('zone_itinerary', 2, 'bootstrap', 'Measuring destination'),
            ('zone_itinerary', 2, 'walking', 'Travel'),
            ('zone_itinerary', 2, 'crossing', 'Crossing'),
            ('zone_itinerary', 2, 'loading', 'Loading zone'),
            ('zone_itinerary', 2, 'arrival', 'Checking arrival'),
            ('zone_itinerary', 2, 'stopping', 'Releasing movement'),
        ):
            state = 'stopping' if stage == 'stopping' else 'running'
            update(dict(state=state, phase='Zone itinerary · section_handoff', journey_phase=journey_phase,
                journey_destination_id='butcher-gfay-crossing' if leg == 1 else 'gfay-butcher-crushbone-crossing',
                zone_itinerary=dict(leg=leg, legs=2, stage=stage)))
            expected = f'Leg {leg}/2 · {label}'
            assert 'ITINERARY TEST' in window.state_badge.text() and expected in window.state_badge.text()
            assert 'ITINERARY TEST '+state.upper() in window.ap_state.text() and expected in window.ap_state.text()
            assert expected in window.ap_info.text() and 'then stop · no camp' in window.ap_info.text()
            assert expected in window.ap_status.text() and 'section_handoff' not in window.ap_status.text()
            assert 'Stationary camp' not in window.ap_info.text() and 'Camp: stationary start' not in window.ap_info.text()
            for control in (button, window.source_destination, window.continue_camps,
                            window.supervised_source, window.test_location_hotkey):
                assert not control.isEnabled()
            assert window.stationary_camp.isEnabled() and 'Stop travel' in window.stationary_camp.text()
            checks.append('progress-'+stage)
        # Existing stop/toggle jobs stay usable; no GUI key interception is added.
        before = len(posts)
        window.stationary_camp.click()
        assert posts[-1] == ('autopilot_later',)
        for text, job in (('STOP', 'stop'), ('Stop autopilot', 'autopilot_stop')):
            stop = next(v for v in window.findChildren(QPushButton) if v.text() == text)
            assert stop.isEnabled()
            stop.click()
            assert posts[-1] == (job,)
        assert len(posts) == before+3
        checks.append('stop-controls')
        update(dict(state='running', journey_phase='zone_itinerary'))
        assert 'ITINERARY TEST' in window.state_badge.text() and 'ITINERARY TEST' in window.ap_state.text()
        update(dict(state='stopping', journey_phase='zone_itinerary'))
        assert 'ITINERARY TEST STOPPING' in window.ap_state.text()
        assert 'Releasing movement' in window.state_badge.text() and not button.isEnabled()
        update(dict(state='off'))
        assert button.isEnabled() and window.source_destination.isEnabled()
        assert window.supervised_source.isEnabled() and window.test_location_hotkey.isEnabled()
        assert window.continue_camps.isEnabled() and 'Repeat stationary camp' in window.stationary_camp.text()
        for active, preparing in ((True, False), (False, True)):
            update(dict(state='off'), active=active, preparing=preparing)
            assert not button.isEnabled() and not window.supervised_source.isEnabled()
            assert ('ASSIST ON' if active else 'PREPARING') in window.state_badge.text()
        update(dict(state='off'))
        checks.append('idle-controls')

        # All legacy choices keep their original request and continuation rule.
        box = window.source_destination
        assert [box.itemData(i) for i in range(box.count())] == list(DESTINATIONS)
        def accept_legacy(dialog):
            next(v for v in dialog.findChildren(QCheckBox) if v.text().startswith('I will supervise')).setChecked(True)
            return QDialog.DialogCode.Accepted
        QDialog.exec = accept_legacy
        for identifier in DESTINATIONS:
            box.setCurrentIndex(box.findData(identifier))
            is_camp = destination_spec(identifier).arrival_mode == 'camp'
            window.continue_camps.setChecked(True)
            window.configure_supervised_source()
            assert posts[-1] == ('supervised_crushbone_source_travel', dict(
                open_flat_clear=True, destination_id=identifier, continue_camps=is_camp))
            checks.append('legacy-'+identifier)
        for phase in ('source_crossing_handoff', 'source_crossing'):
            update(dict(state='running', journey_phase=phase, journey_destination_id='gfay-crushbone-crossing'))
            assert 'TRAVEL TEST' in window.state_badge.text() and 'TRAVEL TEST' in window.ap_state.text()
            assert 'ITINERARY' not in window.state_badge.text()
        update(dict(state='running', journey_phase='camp'))
        assert 'CAMP TEST' in window.state_badge.text() and 'CAMP TEST' in window.ap_state.text()
        assert 'Repeat stationary camp' in window.stationary_camp.text()
        checks.append('legacy-camp-indicator')
        update(dict(state='off', reason=window.ap_default_status))
        assert window.ap_status.text() == window.ap_default_status
        assert window.worker is None and dialog_images == {'ready', 'disabled'}
        report.with_suffix('.checks.json').write_text(json.dumps(dict(checks=checks,
            entry_provider_wired=True, worker_started=False, game_input_sent=False, settings_saved=False), indent=2))
        assert len(smoke_render) == 1
        QTimer.singleShot = actual_single_shot
        actual_single_shot(0, smoke_render[0])
    except BaseException:
        errors.append(traceback.format_exc())
        app.quit()

QTimer.singleShot(0, exercise)
eql_rotation.run_gui(Settings(game_dir=str(report.parent / 'empty-client')),
                     Catalog([]), smoke_path=report.with_suffix('.png'), smoke_view=(3, 0))
if errors:
    raise AssertionError('\n'.join(errors))
assert len(checks) == 35
'''
    env = dict(os.environ, QT_QPA_PLATFORM='offscreen', PYTHONDONTWRITEBYTECODE='1')
    result = subprocess.run([str(ui_python), '-c', code, str(draft), str(report)],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=40)
    assert result.returncode == 0, result.stdout + result.stderr
    checks = json.loads(report.with_suffix('.checks.json').read_text())
    assert checks['entry_provider_wired'] and len(checks['checks']) == 35
    observed = json.loads(report.read_text())
    assert not observed['worker_started'] and not observed['game_input_sent'] and not observed['settings_saved']
    assert observed['itinerary_button_visible'] and observed['itinerary_button_enabled']
    assert 'Butcherblock' in observed['itinerary_button_text']
    assert len(observed['journey_destination_ids']) == 16
    assert report.with_suffix('.png').is_file()
    assert report.with_suffix('.dialog-disabled.png').is_file()
    assert report.with_suffix('.dialog-ready.png').is_file()
    for name in ('rotation_core.py', 'launch.sh'):
        assert sha256((draft / name).read_bytes()).digest() == sha256((source / name).read_bytes()).digest()
    assert sha256((draft / 'rotation_engine.py').read_bytes()).hexdigest() == (
        'd4925d8250e69d6e631f64b4c7eea115b34473aef90d86c9838c045ad355309e')
    info = json.loads((draft / 'BUILD_INFO.json').read_text())
    assert info['version'] == '0.39.43' and info['source_version'] == '0.42.95'
    assert 'F8 owner-targeted assist' in info['mode']
    assert 'Butcherblock → Greater Faydark → Clan Crushbone itinerary, then stop without camping' in info['mode']
    assert info['real_itinerary_acceptance'] is False
    assert info['source_manifest_sha256'] == sha256((draft / 'SOURCE_HASHES.json').read_bytes()).hexdigest()
    assert info['entry_sha256'] == sha256((draft / 'owner_nov12_entry.py').read_bytes()).hexdigest()
