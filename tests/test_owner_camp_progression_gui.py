"""Exercise the separate camp-progression preview action offscreen, without an engine."""
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


PROJECT = Path(__file__).resolve().parents[1]
STORE = Path.home() / '.local/share/eql-automation'


def test_camp_progression_preview_declarations_level_guard_and_camp_handoff(tmp_path):
    source = STORE / 'owner-assist/0.39.13'
    ui_python = STORE / 'python-ui/bin/python'
    if not source.is_dir() or not ui_python.is_file():
        pytest.skip('Pinned retained preview and isolated Qt environment unavailable')
    draft = tmp_path / 'preview'
    subprocess.run([
        sys.executable, str(PROJECT / 'tools/build_nov12_preview_03945.py'),
        '--source', str(source), '--output', str(draft),
    ], cwd=PROJECT, check=True, capture_output=True, text=True)
    report = tmp_path / 'gui.json'
    code = r'''
import json
from pathlib import Path
import sys
import traceback
import time

draft, report = map(Path, sys.argv[1:])
sys.path.insert(0, str(draft))
from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QApplication, QCheckBox, QDialog, QDialogButtonBox, QLabel, QPushButton, QScrollArea
import owner_nov12_entry
owner_nov12_entry.verify_snapshot(draft)
import rotation_engine
from rotation_core import Catalog, Settings
import leveling_guide
import eql_rotation
import eql_automation.owner_journey_runtime as journey_module
import eql_automation.owner_zone_itinerary_assets as plan_module
import eql_automation.owner_camp_progression as progression_module
import eql_automation.owner_camp_progression_assets as progression_assets
from eql_automation.source_destinations import DESTINATIONS, destination_spec

def forbidden(*args, **kwargs):
    raise AssertionError('GUI-only test must not create an engine, load a trip or save settings')
rotation_engine.Engine = forbidden
Settings.save = forbidden
leveling_guide.default_guide = lambda: None
# Exercise the actual built entry after verifying its full source snapshot.
# Its engine factory is captured, and the application entry is a no-op.
wiring, wrappers, launched = [], [], []
journey_marker = object()
actual_factory, actual_main = journey_module.make_owner_journey_engine, eql_rotation.main
actual_provider = plan_module.load_owner_zone_itinerary
actual_wrapper = progression_module.make_camp_progression_engine
def capture_factory(base, **kwargs):
    wiring.append((base, kwargs))
    return journey_marker
def capture_wrapper(base, **kwargs):
    wrappers.append((base, kwargs))
    return forbidden
progression_module.make_camp_progression_engine = capture_wrapper
journey_module.make_owner_journey_engine = capture_factory
eql_rotation.main = lambda: launched.append(True)
saved_argv = sys.argv
try:
    sys.argv = [str(draft / 'owner_nov12_entry.py')]
    assert owner_nov12_entry.main() == 0
finally:
    sys.argv = saved_argv
    journey_module.make_owner_journey_engine = actual_factory
    progression_module.make_camp_progression_engine = actual_wrapper
    eql_rotation.main = actual_main
assert len(wiring) == 1 and wiring[0][0] is forbidden
assert wiring[0][1]['zone_itinerary_provider'] is actual_provider
assert wrappers == [(journey_marker, dict(clock=time.monotonic))]
assert launched == [True]
# The GUI must use profile metadata only, never call a plan/asset loader.
plan_module.load_owner_zone_itinerary = forbidden
progression_assets.load_owner_camp_progression = forbidden
progression_assets.load_camp_origin_itinerary = forbidden
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
        window = next(w for w in app.topLevelWidgets() if hasattr(w, 'camp_progression_start'))
        assert window.worker is None
        button = window.camp_progression_start
        assert button.objectName() == 'campProgressionButton' and button.isEnabled()
        assert all(name in button.text() for name in ('Newbie', 'Goblin', 'Slave Mines'))
        help_text = window.camp_progression_help.text()
        lower = help_text.lower()
        assert '6 hours 15 minutes' in help_text
        assert 'only navigation from goblin camp onward is capped' in lower and 'not an eta' in lower
        assert 'excludes the initial newbie hills approach' in lower
        assert 'later travel to goblin camp and all camping time' in lower
        assert 'changing the configured level alone never starts' in lower
        assert '1–4' in help_text and 'observed level 20' in lower
        assert 'spell' in lower and 'observed' in lower and 'target' in lower
        assert 'unverified' in lower and 'F8' in help_text and 'F9/F11' in help_text
        assert window.zone_itinerary_help.text() == eql_rotation.owner_itinerary_help()
        assert window.terminal_itinerary_help.text() == eql_rotation.owner_terminal_itinerary_help()
        posts, dialog_images, active_images = [], set(), {}
        window.post = lambda *args: posts.append(args)

        def update(payload, *, active=False, preparing=False, level=None):
            window.update_state(dict(status='Synthetic GUI state', active=active, preparing=preparing,
                known=None, prepared=False, level=window.settings.level if level is None else level,
                profile={}, hp=None, mana=None, stance_keys_verified=False, autopilot=payload))

        # The old destination and continuation controls never select progression.
        window.source_destination.setCurrentIndex(window.source_destination.findData('slave-mines'))
        window.continue_camps.setChecked(True)
        update(dict(state='off'), level=4)

        def dialog_result(ground_value, supervision_value, accepted=True, late_change=None):
            def finish(dialog):
                assert dialog.objectName() == 'campProgressionDialog'
                assert all(name in dialog.windowTitle() for name in ('Newbie', 'Goblin', 'Slave Mines'))
                labels = '\n'.join(v.text() for v in dialog.findChildren(QLabel))
                assert help_text in labels and '/location' in labels
                ground = dialog.findChild(QCheckBox, 'campProgressionGroundDeclaration')
                supervision = dialog.findChild(QCheckBox, 'campProgressionSupervisionDeclaration')
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
                    # Do not refresh the button: the posting guard must read
                    # current configured level after the dialog returns.
                    window.settings.level = 5
                return QDialog.DialogCode.Accepted if accepted else QDialog.DialogCode.Rejected
            return finish

        for ground, supervision, accepted in ((False, False, True), (True, False, True),
                                              (False, True, True), (True, True, False)):
            QDialog.exec = dialog_result(ground, supervision, accepted)
            before = len(posts)
            window.configure_camp_progression()
            assert len(posts) == before
            checks.append('progression-declaration-refusal')
        for level, old_continue in ((1, False), (4, True)):
            update(dict(state='off'), level=level)
            window.continue_camps.setChecked(old_continue)
            QDialog.exec = dialog_result(True, True)
            before = len(posts)
            button.click()
            assert len(posts) == before+1
            assert posts[-1] == ('camp_progression', dict(
                progression_id='butcher-newbie-goblin-slave-mines',
                open_flat_clear=True, owner_supervised_continuation=True))
            checks.append('exact-progression-request-level-'+str(level))
        for change in ('level', 'busy'):
            update(dict(state='off'), level=4)
            QDialog.exec = dialog_result(True, True, late_change=change)
            before = len(posts)
            window.configure_camp_progression()
            assert len(posts) == before
            checks.append('late-'+change+'-refusal')
        QDialog.exec = forbidden
        before = len(posts)
        window.configure_camp_progression()
        assert len(posts) == before
        checks.append('busy-direct-callback-refusal')

        for level in (5, 19, 20, 50):
            update(dict(state='off'), level=level)
            assert not button.isEnabled() and window.zone_itinerary_start.isEnabled()
            assert window.terminal_itinerary_start.isEnabled() == (level < 20)
            before = len(posts)
            window.configure_camp_progression()
            assert len(posts) == before
            checks.append('level-'+str(level)+'-refusal')
        for invalid in (0, True, 4.0, '4', 5):
            update(dict(state='off'), level=4)
            assert button.isEnabled()
            # A stale enabled button cannot bypass strict integer level 1..4.
            window.settings.level = invalid
            before = len(posts)
            window.configure_camp_progression()
            assert len(posts) == before
            checks.append('stale-enabled-level-refusal-'+repr(invalid))

        # The pre-existing stop-only and terminal-camp actions remain distinct.
        update(dict(state='off'), level=19)
        for control, dialog_name, ground_name, supervision_name, identifier in (
            (window.zone_itinerary_start, 'zoneItineraryDialog', 'itineraryGroundDeclaration',
             'itinerarySupervisionDeclaration', 'butcher-gfay-crushbone'),
            (window.terminal_itinerary_start, 'terminalItineraryDialog', 'terminalItineraryGroundDeclaration',
             'terminalItinerarySupervisionDeclaration', 'butcher-gfay-crushbone-slave-mines-camp'),
        ):
            def accept_existing(dialog):
                assert dialog.objectName() == dialog_name
                dialog.findChild(QCheckBox, ground_name).setChecked(True)
                dialog.findChild(QCheckBox, supervision_name).setChecked(True)
                return QDialog.DialogCode.Accepted
            QDialog.exec = accept_existing
            before = len(posts)
            control.click()
            assert len(posts) == before+1
            assert posts[-1] == ('zone_itinerary', dict(itinerary_id=identifier,
                open_flat_clear=True, owner_supervised_continuation=True))
            checks.append('unchanged-'+identifier+'-request')
        update(dict(state='off'), level=4)

        statuses = [
            ('newbie_request', 'running', 'travel', 'newbie-hills', None, 'Travel to Newbie Hills'),
            ('newbie_camp', 'running', 'camp', 'newbie-hills', None,
             'Newbie Hills camp · observed level 5 departure after recovery'),
            ('newbie_camp', 'running', 'camp_section_handoff', 'newbie-hills', None, 'Travel to Goblin Camp'),
            ('newbie_camp', 'running', 'camp_walking_sections', 'newbie-hills', None, 'Travel to Goblin Camp'),
            ('newbie_camp', 'running', 'camp', 'goblin-camp', None, 'Travel to Goblin Camp'),
            ('goblin_camp', 'running', 'camp', 'goblin-camp', None,
             'Goblin Camp · observed level 9 or 10 departure after recovery'),
            ('origin_claimed', 'running', 'handoff', 'goblin-camp', None, 'Measuring departure from Goblin Camp'),
            ('navigating', 'running', 'travel', 'slave-mines', None, 'Travel to Slave Mines'),
            # The intent alone keeps every start control locked, even before
            # an underlying journey or running state is available.
            ('future_unknown_phase', 'off', None, None, None, 'Early camp progression'),
        ]
        for leg, stage, label in ((1, 'bootstrap', 'Measuring destination'),
                                   (2, 'crossing', 'Crossing'), (3, 'arrival', 'Checking arrival')):
            trip = dict(record_id='butcher-goblin-gfay-crushbone-slave-mines-camp',
                        leg=leg, legs=3, stage=stage)
            statuses.append(('navigating', 'running', 'zone_itinerary', 'slave-mines', trip,
                             f'Goblin onward · Leg {leg}/3 · {label}'))
        statuses.extend([
            ('cancelled', 'off', None, None, None, 'Releasing movement'),
            ('navigating', 'stopping', 'zone_itinerary', 'slave-mines',
             dict(record_id='butcher-goblin-gfay-crushbone-slave-mines-camp', leg=3, legs=3, stage='walking'),
             'Releasing movement'),
        ])
        QDialog.exec = forbidden
        for phase, state, journey_phase, destination, trip, expected in statuses:
            payload = dict(state=state, phase='Internal controller stage', journey_phase=journey_phase,
                journey_destination_id=destination, progress_summary='3 kills · 120 XP',
                camp_progression=dict(progression_id='butcher-newbie-goblin-slave-mines',
                    phase=phase, root_started=trip is not None, real_client_accepted=False))
            if trip is not None:
                payload['zone_itinerary'] = trip
            update(payload)
            label = {'running': 'RUNNING', 'stopping': 'STOPPING', 'off': 'OFF'}[state]
            assert 'PROGRESSION TEST' in window.state_badge.text() and expected in window.state_badge.text()
            assert 'PROGRESSION TEST '+label in window.ap_state.text() and expected in window.ap_state.text()
            assert expected in window.ap_info.text() and 'Slave Mines' in window.ap_info.text()
            assert 'observed level 20' in window.ap_info.text() and 'no further relocation' in window.ap_info.text()
            if journey_phase == 'camp':
                assert '3 kills · 120 XP' in window.ap_info.text()
            assert expected in window.ap_status.text() and 'Internal controller stage' not in window.ap_status.text()
            for control in (button, window.zone_itinerary_start, window.terminal_itinerary_start,
                            window.source_destination, window.continue_camps,
                            window.supervised_source, window.test_location_hotkey):
                assert not control.isEnabled()
            assert window.stationary_camp.isEnabled() and 'Stop progression' in window.stationary_camp.text()
            before = len(posts)
            window.configure_camp_progression()
            assert len(posts) == before
            image_kind = ('camp' if phase == 'newbie_camp' and journey_phase == 'camp'
                          and destination == 'newbie-hills' else
                          'onward' if trip is not None and trip['leg'] == 1 else None)
            if image_kind is not None:
                page = window.tabs.currentWidget()
                if isinstance(page, QScrollArea):
                    page.verticalScrollBar().setValue(0)
                app.processEvents()
                legend = window.findChild(QLabel, 'hotkeyLegend')
                assert legend is not None and all(key in legend.text() for key in ('F6', 'F7', 'F8', 'F9', 'F10', 'F11', 'F12'))
                for label in (window.state_badge, legend, window.ap_state):
                    flags = Qt.TextFlag.TextWordWrap if label.wordWrap() else Qt.TextFlag.TextSingleLine
                    available = label.contentsRect()
                    required = label.fontMetrics().boundingRect(available, flags, label.text())
                    assert required.width() <= available.width() and required.height() <= available.height(), (
                        label.text(), required.getRect(), available.getRect())
                screenshot = window.grab()
                assert screenshot.save(str(report.with_suffix('.active-'+image_kind+'.png')))
                active_images[image_kind] = dict(width=screenshot.width(), height=screenshot.height())
            checks.append('progression-status-'+phase+'-'+str(journey_phase))

        before = len(posts)
        window.stationary_camp.click()
        assert posts[-1] == ('autopilot_later',)
        for text, job in (('STOP', 'stop'), ('Stop autopilot', 'autopilot_stop')):
            stop = next(v for v in window.findChildren(QPushButton) if v.text() == text)
            assert stop.isEnabled(); stop.click(); assert posts[-1] == (job,)
        assert len(posts) == before+3
        checks.append('progression-stop-controls')

        # Consumed progression no longer covers the terminal camp's own status.
        for phase in (None, 'consumed', 'terminal_camp'):
            payload = dict(state='running', phase='Preparing learned spells at Slave Mines', journey_phase='camp',
                journey_destination_id='slave-mines', journey_continue_camps=False,
                arrival_destination=dict(name='Slave Mines'), camp=dict(id='slave-mines', name='Slave Mines'))
            if phase is not None:
                payload['camp_progression'] = dict(progression_id='butcher-newbie-goblin-slave-mines',
                    phase=phase, root_started=True, real_client_accepted=False)
            update(payload)
            assert 'CAMP TEST' in window.state_badge.text() and 'CAMP TEST' in window.ap_state.text()
            assert 'PROGRESSION' not in window.state_badge.text() and 'PROGRESSION' not in window.ap_state.text()
            assert 'Slave Mines' in window.ap_state.text() and 'Slave Mines' in window.ap_info.text()
            assert 'Preparing learned spells' in window.ap_status.text()
            assert 'Repeat stationary camp' in window.stationary_camp.text() and not button.isEnabled()
            checks.append('normal-terminal-camp-'+str(phase))

        for identifier, ending in (
            ('butcher-gfay-crushbone', 'Finish in Clan Crushbone, then stop · no camp'),
            ('butcher-gfay-crushbone-slave-mines-camp', 'Slave Mines · prepare learned spells, then stationary camp'),
        ):
            update(dict(state='running', journey_phase='zone_itinerary',
                zone_itinerary=dict(record_id=identifier, leg=2, legs=2, stage='walking')))
            assert 'ITINERARY TEST' in window.state_badge.text() and 'ITINERARY TEST' in window.ap_state.text()
            assert 'PROGRESSION' not in window.state_badge.text() and ending in window.ap_info.text()
            assert 'Stop travel' in window.stationary_camp.text()
            checks.append('existing-itinerary-status-'+identifier)

        update(dict(state='off'), level=4)
        for active, preparing in ((True, False), (False, True)):
            update(dict(state='off'), active=active, preparing=preparing)
            assert not button.isEnabled()
            assert not window.zone_itinerary_start.isEnabled() and not window.terminal_itinerary_start.isEnabled()
            assert ('ASSIST ON' if active else 'PREPARING') in window.state_badge.text()
            checks.append('owner-busy-refusal')
        update(dict(state='off'), level=4)
        assert button.isEnabled() and window.zone_itinerary_start.isEnabled() and window.terminal_itinerary_start.isEnabled()

        # All sixteen ordinary source-destination requests remain unchanged.
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
        update(dict(state='off', reason=window.ap_default_status), level=4)
        assert window.ap_status.text() == window.ap_default_status
        assert window.worker is None and dialog_images == {'ready', 'disabled'}
        assert set(active_images) == {'camp', 'onward'}
        page = window.tabs.currentWidget()
        if isinstance(page, QScrollArea):
            page.verticalScrollBar().setValue(max(0, button.y()-24))
        app.processEvents()
        report.with_suffix('.checks.json').write_text(json.dumps(dict(checks=checks,
            entry_provider_wired=True, progression_wrapper_wired=True, progression_button_enabled=button.isEnabled(),
            progression_button_text=button.text(), progression_help=help_text, active_images=active_images,
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
assert len(checks) == 58
'''
    env = dict(os.environ, QT_QPA_PLATFORM='offscreen', PYTHONDONTWRITEBYTECODE='1')
    result = subprocess.run([str(ui_python), '-c', code, str(draft), str(report)],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=40)
    assert result.returncode == 0, result.stdout + result.stderr
    checks = json.loads(report.with_suffix('.checks.json').read_text())
    assert checks['entry_provider_wired'] and checks['progression_wrapper_wired']
    assert len(checks['checks']) == 58
    observed = json.loads(report.read_text())
    assert not observed['worker_started'] and not observed['game_input_sent'] and not observed['settings_saved']
    assert observed['itinerary_button_visible'] and observed['itinerary_button_enabled']
    assert 'Butcherblock' in observed['itinerary_button_text']
    assert checks['progression_button_enabled'] and 'Slave Mines' in checks['progression_button_text']
    assert len(observed['journey_destination_ids']) == 16
    assert report.with_suffix('.png').is_file()
    assert report.with_suffix('.dialog-disabled.png').is_file()
    assert report.with_suffix('.dialog-ready.png').is_file()
    assert report.with_suffix('.active-camp.png').is_file()
    assert report.with_suffix('.active-onward.png').is_file()
    for name in ('rotation_core.py', 'launch.sh'):
        assert sha256((draft / name).read_bytes()).digest() == sha256((source / name).read_bytes()).digest()
    assert sha256((draft / 'rotation_engine.py').read_bytes()).hexdigest() == (
        'd4925d8250e69d6e631f64b4c7eea115b34473aef90d86c9838c045ad355309e')
    info = json.loads((draft / 'BUILD_INFO.json').read_text())
    from eql_automation import __version__ as source_version
    assert info['version'] == '0.39.45' and info['source_version'] == source_version
    assert 'F8 owner-targeted assist' in info['mode']
    assert 'Butcherblock → Greater Faydark → Clan Crushbone itinerary, then stop without camping' in info['mode']
    assert info['real_itinerary_acceptance'] is False
    assert 'Slave Mines' in info['mode'] and 'camp' in info['mode']
    assert info['real_terminal_camp_acceptance'] is False
    assert info['real_camp_progression_acceptance'] is False
    assert 'Newbie' in info['mode'] and 'Goblin' in info['mode']
    assert info['source_manifest_sha256'] == sha256((draft / 'SOURCE_HASHES.json').read_bytes()).hexdigest()
    assert info['entry_sha256'] == sha256((draft / 'owner_nov12_entry.py').read_bytes()).hexdigest()
