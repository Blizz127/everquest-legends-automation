from hashlib import sha256
from types import MappingProxyType

from PIL import Image
import pytest

from test_chat_ui_layout import layout as chat_layout
from test_ui_frame_features import h, gauge_reader
from eql_automation.chat_ui_layout import COPIED_RUNTIME_SHA256, Edges
from eql_automation.ui_frame_features import PreparedUiFrameReader
from eql_automation.prepared_ui_layout import PreparedLayoutView
import eql_automation.ui_frame_features as features


@pytest.fixture
def combined(h,chat_layout):
    for name in ('elements','screen_for','_to_screen'):
        setattr(h.layout,name,getattr(chat_layout,name))
    h.layout._window_box=lambda name:Edges(0,200,600,500)
    h.layout.ui_scale=1.25
    h.layout.sources.update({name:h.xml for name in h.layout.elements})
    h.chat_read=lambda:h.read(chat_runtime_sha256=COPIED_RUNTIME_SHA256)
    return h


def test_chat_uses_same_new_frame_without_saving_pixels_or_inferring_focus(combined,monkeypatch):
    h=combined
    monkeypatch.setattr(Image.Image,'save',lambda *a,**k:pytest.fail('Chat pixels saved'))
    first=h.chat_read()
    assert h.captures==1
    chat=first['chat_input']
    assert chat['status']=='source_geometry_proposal'
    assert chat['frame_rgb_sha256']==first['frame_rgb_sha256']
    assert chat['focus']==chat['draft']==first['chat_state']=='unknown'
    assert not chat['pixel_values_saved'] and not chat['text_recognized'] and not chat['input_authorized']
    box=chat['regions']['outer']['box']
    assert chat['regions']['outer']['rgb_sha256']==sha256(h.frame.crop(box).tobytes()).hexdigest()
    h.frame.putpixel((box[0]+1,box[1]+1),(255,255,255))
    second=h.chat_read()
    assert h.captures==2
    assert second['chat_input']['regions']['outer']['rgb_sha256']!=chat['regions']['outer']['rgb_sha256']
    assert second['chat_input']['focus']=='unknown' and second['chat_state']=='unknown'
    assert sorted(p.name for p in h.game.iterdir())==['player.xml']


def test_chat_geometry_work_counts_toward_complete_observation_budget(combined,monkeypatch):
    h=combined;original=features.chat_regions_from_sample
    def slow(*args,**kwargs):
        h.now+=.2
        return original(*args,**kwargs)
    monkeypatch.setattr(features,'chat_regions_from_sample',slow)
    result=h.chat_read()
    assert result['total_seconds']==pytest.approx(.2)
    assert not result['within_100ms_sample_budget']


@pytest.mark.parametrize('change',['missing-provenance','offscreen','missing-source','unknown-runtime'])
def test_unavailable_chat_preserves_gauges_but_never_grants_clear(combined,change):
    h=combined;runtime=COPIED_RUNTIME_SHA256
    if change=='missing-provenance':del h.layout.sources['inputLeft']
    elif change=='offscreen':h.layout._window_box=lambda name:Edges(1000,200,1600,500)
    elif change=='missing-source':del h.layout.elements['inputLeft']
    else:runtime='0'*64
    result=h.read(chat_runtime_sha256=runtime)
    assert result['chat_input']['status']=='unavailable' and result['chat_input']['reason']
    assert result['gauges']['hp']['fraction_candidate']==.5
    assert result['chat_input']['focus']==result['chat_state']=='unknown'
    assert not result['g2_safety_flags_provided'] and not result['input_authorized']


@pytest.mark.parametrize('mutation',['source','frame'])
def test_consistency_checks_include_chat_feature_pass(combined,monkeypatch,mutation):
    h=combined;original=features.chat_regions_from_sample
    def changed(sample,**kwargs):
        regions=original(sample,**kwargs)
        if mutation=='source':h.xml.write_text('changed source')
        else:sample.image.putpixel((799,599),(7,8,9))
        return regions
    monkeypatch.setattr(features,'chat_regions_from_sample',changed)
    with pytest.raises((ValueError,RuntimeError),match='changed'):h.chat_read()


def test_prepared_reader_passes_explicit_copied_runtime_context(combined):
    h=combined
    reader=PreparedUiFrameReader(**h.args,atlas=h.a,gauge_reader=h.reader,
        saved_scale=1.25,chat_runtime_sha256=COPIED_RUNTIME_SHA256)
    assert h.captures==0
    result=reader()
    assert h.captures==1 and result['chat_input']['status']=='source_geometry_proposal'
    assert result['reader_preparation']['contains_scene_observation'] is False


def test_default_reader_does_not_request_chat_geometry(h,monkeypatch):
    monkeypatch.setattr(features,'chat_regions_from_sample',lambda *a,**k:pytest.fail('Unrequested chat read'))
    result=h.read()
    assert result['chat_input']==dict(status='not_requested',focus='unknown',draft='unknown')


@pytest.mark.parametrize('changed',[False,True])
def test_frame_reader_rechecks_prepared_dependency_snapshot_after_features(combined,monkeypatch,changed):
    h=combined;calls=[];original=h.layout
    # This file represents a loaded include with no surviving definitions;
    # it is deliberately absent from original.sources.
    extra=h.game/'empty-include.xml';extra.write_text('<XML/>')
    hashes={str(p):sha256(p.read_bytes()).hexdigest() for p in (h.xml,extra)}
    def verify():
        calls.append('verify');h.now+=.02
        if changed:raise RuntimeError('Prepared source overlay changed')
        return hashes
    prep=dict(seconds=.3,contains_scene_observation=False)
    h.layout=PreparedLayoutView(original,MappingProxyType(hashes),verify,prep)
    if changed:
        with pytest.raises(RuntimeError,match='overlay changed'):h.chat_read()
    else:
        result=h.chat_read()
        assert result['layout_preparation']==prep
        assert str(extra) in result['source_sha256_postcapture']
        assert result['total_seconds']==pytest.approx(.02)
        assert result['chat_input']['status']=='source_geometry_proposal'
    assert calls==['verify'] and h.captures==1
