from hashlib import sha256
import importlib.util
from pathlib import Path
import sys

import pytest

from eql_automation.prepared_ui_layout import PreparedUiLayout


@pytest.fixture(scope='module')
def retained_layout():
    path=Path.home()/'.local/share/eql-automation/owner-assist/0.39.10/uilayout.py'
    if not path.exists():pytest.skip('Retained layout loader unavailable')
    assert sha256(path.read_bytes()).hexdigest()=='d79ec2ae32a31fa642f4b64952996c28d7905efc15fce1d816fc671e552b733a'
    spec=importlib.util.spec_from_file_location('prepared_retained_layout',path)
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    return module.UiLayout


@pytest.fixture
def inputs(tmp_path,retained_layout):
    from types import SimpleNamespace
    h=SimpleNamespace(game=tmp_path/'game',calls=0)
    h.default=h.game/'uifiles/default';h.default.mkdir(parents=True)
    h.skin=h.game/'uifiles/custom';h.skin.mkdir()
    h.ini=h.game/'UI_Test_private_suffix.ini'
    h.ini.write_text('[Main]\nUISkin=custom\n[Window]\nXPos=10\nYPos=20\n')
    h.client=h.game/'eqclient.ini';h.client.write_text('[Defaults]\nUIScale=1\n')
    h.manifest=h.default/'EQUI.xml';h.manifest.write_text('<XML><Include>EQUI_Window.xml</Include><Include>sub/last.dat</Include></XML>')
    h.xml=h.default/'EQUI_Window.xml';h.xml.write_text('<XML><Screen item="Window"><Size><CX>200</CX><CY>150</CY></Size></Screen><Label item="overridden"/></XML>')
    h.last=h.default/'sub/last.dat';h.last.parent.mkdir();h.last.write_text('<XML><Label item="overridden"/></XML>')
    class Counted(retained_layout):
        @classmethod
        def load(cls,*args,**kwargs):
            h.calls+=1
            return super().load(*args,**kwargs)
    h.kind=Counted
    h.prepare=lambda:PreparedUiLayout(h.kind,game=h.game,character='Test',server='private',width=800,height=600)
    h.read=lambda cache:cache(h.game,'Test','private',width=800,height=600)
    return h


def test_prepared_layout_reuses_parse_but_returns_independent_layout_caches_and_ini(inputs):
    h=inputs;cache=h.prepare();a=h.read(cache);b=h.read(cache)
    assert h.calls==1 and a.layout is not b.layout and a.ini is not b.ini
    assert a.window('Window')==b.window('Window')
    a.layout._page_border['example']=(1,2,3,4)
    a.ini.set('Window','XPos','999')
    assert not b.layout._page_border and b.ini.get('Window','XPos')=='10'
    assert str(h.last) in a.source_hashes and str(h.manifest) in a.source_hashes
    assert not cache.preparation['contains_scene_observation']
    assert a.source_verifier()==dict(a.source_hashes)


@pytest.mark.parametrize('change',['content','fully-overridden','manifest','new-skin-manifest',
    'new-exact-ini','ambiguous-ini','client','new-skin-override','new-default-variant','new-skin-variant'])
def test_cache_invalidates_all_selection_and_content_dependencies(inputs,change):
    h=inputs
    # Default variant must outrank an existing normal selected-skin file.
    if change in ('new-default-variant','new-skin-variant'):
        h.ini.write_text(h.ini.read_text()+'\n[Default]\nWindow=2\n')
        (h.skin/'EQUI_Window.xml').write_text(h.xml.read_text())
    if change=='fully-overridden':h.xml.write_text('<XML><Label item="overridden"/></XML>')
    cache=h.prepare();view=h.read(cache)
    if change in ('content','fully-overridden'):h.xml.write_text(h.xml.read_text().replace('</XML>','<Label item="new"/></XML>'))
    elif change=='manifest':h.manifest.write_text('<XML><Include>sub/last.dat</Include></XML>')
    elif change=='new-skin-manifest':(h.skin/'EQUI.xml').write_text(h.manifest.read_text())
    elif change=='new-exact-ini':(h.game/'UI_Test_private.ini').write_text(h.ini.read_text())
    elif change=='ambiguous-ini':(h.game/'UI_Test_private_other.ini').write_text(h.ini.read_text())
    elif change=='client':h.client.write_text('[Defaults]\nUIScale=2\n')
    elif change=='new-skin-override':(h.skin/'EQUI_Window.xml').write_text(h.xml.read_text())
    elif change=='new-default-variant':(h.default/'EQUI_Window2.xml').write_text(h.xml.read_text())
    elif change=='new-skin-variant':(h.skin/'EQUI_Window2.xml').write_text(h.xml.read_text())
    with pytest.raises(RuntimeError):h.read(cache)
    # End-of-frame revalidation covers the same whole fingerprint.
    with pytest.raises(RuntimeError):view.source_verifier()
    assert h.calls==1


def test_empty_skin_manifest_remains_a_dependency(inputs):
    h=inputs;manifest=h.skin/'EQUI.xml';manifest.write_text('<XML/>')
    cache=h.prepare();view=h.read(cache)
    assert str(manifest) in view.source_hashes and str(h.manifest) in view.source_hashes
    manifest.write_text(h.manifest.read_text())
    with pytest.raises(RuntimeError):view.source_verifier()


def test_missing_skin_directory_creation_changes_fallback(inputs):
    h=inputs;h.skin.rmdir();cache=h.prepare()
    h.skin.mkdir()
    with pytest.raises(RuntimeError):h.read(cache)


def test_missing_client_ini_creation_is_detected(inputs):
    h=inputs;h.client.unlink();cache=h.prepare()
    h.client.write_text('[Defaults]\nUIScale=1\n')
    with pytest.raises(RuntimeError):h.read(cache)


def test_binding_and_resolution_are_fixed(inputs):
    h=inputs;cache=h.prepare()
    with pytest.raises(RuntimeError,match='binding'):
        cache(h.game,'Test','private',width=801,height=600)
    with pytest.raises(RuntimeError,match='binding'):
        cache(h.game,'Other','private',width=800,height=600)


def test_source_change_during_initial_parse_is_not_cached(inputs):
    h=inputs;original=h.kind.load
    def changed(*a,**k):
        value=original(*a,**k);h.xml.write_text(h.xml.read_text()+'\n');return value
    h.kind.load=changed
    with pytest.raises(RuntimeError,match='during layout preparation'):h.prepare()


def test_no_source_outside_bound_client_directory_is_read(inputs):
    h=inputs;h.manifest.write_text('<XML><Include>../../../outside.dat</Include></XML>')
    with pytest.raises(ValueError,match='leaves'):h.prepare()


def test_compiled_verification_never_reparses_unchanged_ini_or_manifest(inputs,monkeypatch):
    import eql_automation.prepared_ui_layout as prepared
    h=inputs;cache=h.prepare()
    monkeypatch.setattr(cache,'_snapshot',lambda:pytest.fail('Selection plan rebuilt inside observation'))
    monkeypatch.setattr(prepared.RawConfigParser,'read_string',lambda *a,**k:pytest.fail('INI reparsed'))
    monkeypatch.setattr(prepared.ET,'fromstring',lambda *a,**k:pytest.fail('Manifest reparsed'))
    assert h.read(cache).source_verifier()==cache._fingerprint['files']
    assert h.calls==1


def test_same_content_symlink_replacement_invalidates_cached_source_identity(inputs):
    h=inputs
    first=h.default/'first.xml';second=h.default/'second.xml'
    first.write_bytes(h.xml.read_bytes());second.write_bytes(first.read_bytes())
    h.xml.unlink();h.xml.symlink_to(first.name)
    cache=h.prepare();view=h.read(cache)
    h.xml.unlink();h.xml.symlink_to(second.name)
    with pytest.raises(RuntimeError,match='identity changed'):view.source_verifier()
