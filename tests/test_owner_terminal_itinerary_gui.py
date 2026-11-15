"""Exercise the separate terminal-camp preview action offscreen, without an engine."""
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


PROJECT = Path(__file__).resolve().parents[1]
STORE = Path.home() / '.local/share/eql-automation'


def test_terminal_itinerary_preview_declarations_level_guard_and_camp_handoff(tmp_path):
    source = STORE / 'owner-assist/0.39.13'
    ui_python = STORE / 'python-ui/bin/python'
    if not source.is_dir() or not ui_python.is_file():
        pytest.skip('Pinned retained preview and isolated Qt environment unavailable')
    draft = tmp_path / 'preview'
    subprocess.run([
        sys.executable, str(PROJECT / 'tools/build_nov12_preview_03944.py'),
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
from PySide6.QtWidgets import QApplication, QCheckBox, QDialog, QDialogButtonBox, QLabel, QPushButton, QScrollArea
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
        window = next(w for w in app.topLevelWidgets() if hasattr(w, 'terminal_itinerary_start'))
        assert window.worker is None
        button = window.terminal_itinerary_start
        assert button.objectName() == 'terminalItineraryButton' and button.isEnabled()
        assert 'Butcherblock' in button.text() and 'Slave Mines' in button.text()
        help_text = window.terminal_itinerary_help.text()
        lower = help_text.lower()
        assert '6 hours 18 minutes' in help_text
        assert 'maximum' in lower and 'estimate' in lower and 'navigation' in lower
        assert 'configured level must be 1–19' in lower and 'observed level 20' in lower
        assert 'spell' in lower and ('prepare' in lower or 'preparation' in lower)
        assert 'observed' in lower and 'target' in lower
        assert 'next camp' in lower or 'another camp' in lower
        assert 'unverified' in lower and 'F8' in help_text and 'F9/F11' in help_text
        assert window.zone_itinerary_help.text() == eql_rotation.owner_itinerary_help()
        assert '5 hours 28 minutes' in window.zone_itinerary_help.text()
        assert 'then stop without combat or a camp' in window.zone_itinerary_help.text()
        posts, dialog_images = [], set()
        window.post = lambda *args: posts.append(args)

        def update(payload, *, active=False, preparing=False, level=None):
            window.update_state(dict(status='Synthetic GUI state', active=active, preparing=preparing,
                known=None, prepared=False, level=window.settings.level if level is None else level,
                profile={}, hp=None, mana=None, stance_keys_verified=False, autopilot=payload))

        # This unrelated choice must never select or continue the terminal camp.
        window.source_destination.setCurrentIndex(window.source_destination.findData('slave-mines'))
        window.continue_camps.setChecked(True)
        update(dict(state='off'), level=19)

        def dialog_result(ground_value, supervision_value, accepted=True, late_change=None):
            def finish(dialog):
                assert dialog.objectName() == 'terminalItineraryDialog'
                assert 'Slave Mines' in dialog.windowTitle() and 'camp' in dialog.windowTitle().lower()
                labels = '\n'.join(v.text() for v in dialog.findChildren(QLabel))
                assert help_text in labels and '/location' in labels
                ground = dialog.findChild(QCheckBox, 'terminalItineraryGroundDeclaration')
                supervision = dialog.findChild(QCheckBox, 'terminalItinerarySupervisionDeclaration')
                ok = dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Ok)
                assert ground is not None and supervision is not None
                assert not ground.isChecked() and not supervision.isChecked() and not ok.isEnabled()
                ground.setChecked(ground_value)
                assert not ok.isEnabled()
                supervision.setChecked(supervision_value)
                assert ok.isEnabled() == (ground_value and supervision_value)
                image_kind = 'ready' if ground_value and supervision_value else 'disabled'
                if image_kind not in dialog_images:
                    dialog.ensurePolished(); dialog.adjustSize(); dialog.show()
                    app.processEvents()
                    screenshot = dialog.grab()
                    assert screenshot.width() >= 600 and screenshot.height() >= 250
                    assert screenshot.save(str(report.with_suffix('.dialog-'+image_kind+'.png')))
                    dialog.hide(); dialog_images.add(image_kind)
                if late_change == 'busy':
                    window.render_autopilot(dict(state='running', journey_phase='travel'))
                elif late_change == 'level':
                    # No paint/update call: final posting must inspect the level
                    # even if the button's availability has not yet refreshed.
                    window.settings.level = 20
                return QDialog.DialogCode.Accepted if accepted else QDialog.DialogCode.Rejected
            return finish

        for ground, supervision, accepted in ((False, False, True), (True, False, True),
                                              (False, True, True), (True, True, False)):
            QDialog.exec = dialog_result(ground, supervision, accepted)
            before = len(posts)
            window.configure_terminal_itinerary()
            assert len(posts) == before
            checks.append('terminal-declaration-refusal')
        QDialog.exec = dialog_result(True, True)
        button.click()
        assert posts[-1] == ('zone_itinerary', dict(
            itinerary_id='butcher-gfay-crushbone-slave-mines-camp',
            open_flat_clear=True, owner_supervised_continuation=True))
        checks.append('exact-terminal-request')
        for change in ('level', 'busy'):
            update(dict(state='off'), level=19)
            QDialog.exec = dialog_result(True, True, late_change=change)
            before = len(posts)
            window.configure_terminal_itinerary()
            assert len(posts) == before
            checks.append('late-'+change+'-refusal')
        QDialog.exec = forbidden
        before = len(posts)
        window.configure_terminal_itinerary()
        assert len(posts) == before
        checks.append('busy-direct-callback-refusal')

        for level in (20, 21, 50):
            update(dict(state='off'), level=level)
            assert not button.isEnabled() and window.zone_itinerary_start.isEnabled()
            before = len(posts)
            window.configure_terminal_itinerary()
            assert len(posts) == before
            checks.append('level-'+str(level)+'-refusal')
        update(dict(state='off'), level=19)
        assert button.isEnabled()
        # A stale enabled button cannot bypass the slot's initial level check.
        window.settings.level = 20
        before = len(posts)
        window.configure_terminal_itinerary()
        assert len(posts) == before
        checks.append('stale-enabled-level-refusal')

        # Level 20 does not disable the existing stop-only navigation request.
        update(dict(state='off'), level=20)
        def accept_stop_trip(dialog):
            assert dialog.objectName() == 'zoneItineraryDialog'
            dialog.findChild(QCheckBox, 'itineraryGroundDeclaration').setChecked(True)
            dialog.findChild(QCheckBox, 'itinerarySupervisionDeclaration').setChecked(True)
            return QDialog.DialogCode.Accepted
        QDialog.exec = accept_stop_trip
        window.zone_itinerary_start.click()
        assert posts[-1] == ('zone_itinerary', dict(itinerary_id='butcher-gfay-crushbone',
            open_flat_clear=True, owner_supervised_continuation=True))
        checks.append('unchanged-stop-trip-request')
        update(dict(state='off'), level=19)

        for leg, stage, label in (
            (1, 'walking', 'Travel'), (1, 'crossing', 'Crossing'),
            (2, 'bootstrap', 'Measuring destination'), (2, 'crossing', 'Crossing'),
            (3, 'bootstrap', 'Measuring destination'), (3, 'walking', 'Travel'),
            (3, 'arrival', 'Checking arrival'), (3, 'stopping', 'Releasing movement'),
        ):
            state = 'stopping' if stage == 'stopping' else 'running'
            update(dict(state=state, phase='Zone itinerary · terminal_handoff', journey_phase='zone_itinerary',
                journey_destination_id='slave-mines' if leg == 3 else 'gfay-butcher-crushbone-crossing',
                zone_itinerary=dict(record_id='butcher-gfay-crushbone-slave-mines-camp',
                    leg=leg, legs=3, stage=stage, terminal_camp=dict(destination_id='slave-mines', name='Slave Mines'))))
            expected = f'Leg {leg}/3 · {label}'
            assert 'ITINERARY TEST' in window.state_badge.text() and expected in window.state_badge.text()
            assert 'ITINERARY TEST '+state.upper() in window.ap_state.text() and expected in window.ap_state.text()
            assert expected in window.ap_info.text() and 'Slave Mines' in window.ap_info.text()
            assert 'camp' in window.ap_info.text().lower() and 'no camp' not in window.ap_info.text().lower()
            assert expected in window.ap_status.text() and 'terminal_handoff' not in window.ap_status.text()
            for control in (button, window.zone_itinerary_start, window.source_destination,
                            window.continue_camps, window.supervised_source, window.test_location_hotkey):
                assert not control.isEnabled()
            assert window.stationary_camp.isEnabled() and 'Stop travel' in window.stationary_camp.text()
            checks.append('terminal-leg-'+str(leg)+'-'+stage)

        before = len(posts)
        window.stationary_camp.click()
        assert posts[-1] == ('autopilot_later',)
        for text, job in (('STOP', 'stop'), ('Stop autopilot', 'autopilot_stop')):
            stop = next(v for v in window.findChildren(QPushButton) if v.text() == text)
            assert stop.isEnabled(); stop.click(); assert posts[-1] == (job,)
        assert len(posts) == before+3
        checks.append('stop-controls')

        # A stop-only trip must retain its former destination description.
        update(dict(state='running', journey_phase='zone_itinerary',
            zone_itinerary=dict(record_id='butcher-gfay-crushbone', leg=2, legs=2, stage='walking')))
        assert 'Leg 2/2' in window.state_badge.text()
        assert 'Finish in Clan Crushbone, then stop · no camp' in window.ap_info.text()
        checks.append('stop-trip-progress-unchanged')
        # Successful handoff drops itinerary state and uses normal camp rendering.
        update(dict(state='running', phase='Preparing learned spells at Slave Mines', journey_phase='camp',
            journey_destination_id='slave-mines', journey_continue_camps=False,
            arrival_destination=dict(name='Slave Mines'), camp=dict(id='slave-mines', name='Slave Mines')))
        assert 'CAMP TEST' in window.state_badge.text() and 'CAMP TEST' in window.ap_state.text()
        assert 'ITINERARY' not in window.state_badge.text() and 'ITINERARY' not in window.ap_state.text()
        assert 'Slave Mines' in window.ap_state.text() and 'Slave Mines' in window.ap_info.text()
        assert 'Preparing learned spells' in window.ap_status.text()
        assert 'Repeat stationary camp' in window.stationary_camp.text() and not button.isEnabled()
        checks.append('normal-terminal-camp-indicator')

        update(dict(state='off'), level=19)
        for active, preparing in ((True, False), (False, True)):
            update(dict(state='off'), active=active, preparing=preparing)
            assert not button.isEnabled() and not window.zone_itinerary_start.isEnabled()
            assert ('ASSIST ON' if active else 'PREPARING') in window.state_badge.text()
            checks.append('owner-busy-refusal')
        update(dict(state='off'), level=19)
        assert button.isEnabled() and window.zone_itinerary_start.isEnabled()

        # New actions must not change the original sixteen destination requests.
        box = window.source_destination
        assert [box.itemData(i) for i in range(box.count())] == list(DESTINATIONS)
        def accept_legacy(dialog):
            next(v for v in dialog.findChildren(QCheckBox) if v.text().startswith('I will supervise')).setChecked(True)
            return QDialog.DialogCode.Accepted
        QDialog.exec = accept_legacy
        for identifier in DESTINATIONS:
            box.setCurrentIndex(box.findData(identifier))
            window.continue_camps.setChecked(True)
            window.configure_supervised_source()
            assert posts[-1] == ('supervised_crushbone_source_travel', dict(open_flat_clear=True,
                destination_id=identifier, continue_camps=destination_spec(identifier).arrival_mode == 'camp'))
            checks.append('legacy-'+identifier)
        update(dict(state='off', reason=window.ap_default_status), level=19)
        assert window.ap_status.text() == window.ap_default_status
        assert window.worker is None and dialog_images == {'ready', 'disabled'}
        # Keep the new action in view for the final smoke image.
        page = window.tabs.currentWidget()
        if isinstance(page, QScrollArea):
            page.verticalScrollBar().setValue(max(0, button.y()-24))
        app.processEvents()
        report.with_suffix('.checks.json').write_text(json.dumps(dict(checks=checks,
            entry_provider_wired=True, terminal_button_enabled=button.isEnabled(),
            terminal_button_text=button.text(), terminal_help=help_text,
            worker_started=False, game_input_sent=False, settings_saved=False), indent=2))
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
assert len(checks) == 42
'''
    env = dict(os.environ, QT_QPA_PLATFORM='offscreen', PYTHONDONTWRITEBYTECODE='1')
    result = subprocess.run([str(ui_python), '-c', code, str(draft), str(report)],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=40)
    assert result.returncode == 0, result.stdout + result.stderr
    checks = json.loads(report.with_suffix('.checks.json').read_text())
    assert checks['entry_provider_wired'] and len(checks['checks']) == 42
    observed = json.loads(report.read_text())
    assert not observed['worker_started'] and not observed['game_input_sent'] and not observed['settings_saved']
    assert observed['itinerary_button_visible'] and observed['itinerary_button_enabled']
    assert 'Butcherblock' in observed['itinerary_button_text']
    assert checks['terminal_button_enabled'] and 'Slave Mines' in checks['terminal_button_text']
    assert len(observed['journey_destination_ids']) == 16
    assert report.with_suffix('.png').is_file()
    assert report.with_suffix('.dialog-disabled.png').is_file()
    assert report.with_suffix('.dialog-ready.png').is_file()
    for name in ('rotation_core.py', 'launch.sh'):
        assert sha256((draft / name).read_bytes()).digest() == sha256((source / name).read_bytes()).digest()
    assert sha256((draft / 'rotation_engine.py').read_bytes()).hexdigest() == (
        'd4925d8250e69d6e631f64b4c7eea115b34473aef90d86c9838c045ad355309e')
    info = json.loads((draft / 'BUILD_INFO.json').read_text())
    from eql_automation import __version__ as source_version
    assert info['version'] == '0.39.44' and info['source_version'] == source_version
    assert 'F8 owner-targeted assist' in info['mode']
    assert 'Butcherblock → Greater Faydark → Clan Crushbone itinerary, then stop without camping' in info['mode']
    assert info['real_itinerary_acceptance'] is False
    assert 'Slave Mines' in info['mode'] and 'camp' in info['mode']
    assert info['real_terminal_camp_acceptance'] is False
    assert info['source_manifest_sha256'] == sha256((draft / 'SOURCE_HASHES.json').read_bytes()).hexdigest()
    assert info['entry_sha256'] == sha256((draft / 'owner_nov12_entry.py').read_bytes()).hexdigest()
