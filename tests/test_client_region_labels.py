import pytest
from dataclasses import replace

from eql_automation.client_region_labels import ClientRegionMap, decode_client_region_label
from test_region_audit import region_wld


@pytest.mark.parametrize('prefix,code', [('DR',0),('WT',5),('AWT',5),('SL',6),
    ('LA',7),('ALV',7),('VW',8),('AVW',8),('W2',9),('W3',10)])
def test_native_prefix_mapping_preserves_upper_bits(prefix,code):
    result = decode_client_region_label(prefix+'_ZONE', initial_flags=0xa50000ff)
    assert result.flags == 0xa5000000 | code and result.low_byte == code
    assert result.matched_prefix == prefix
    assert not any((result.enum_meaning_verified, result.dry_verified,
                    result.real_client_accepted, result.input_authorized))


@pytest.mark.parametrize('label', [None, '', 'WT', 'AWT', 'wt_zone', 'AXXX'])
def test_absent_short_lowercase_unknown_do_not_create_a_new_type(label):
    result = decode_client_region_label(label, initial_flags=0x12345678)
    assert result.flags == 0x12345678 and result.matched_prefix is None
    assert result.label_present == (label is not None)


def test_zero_default_is_not_dry_evidence():
    result = decode_client_region_label(None)
    assert result.flags == 0 and not result.dry_verified


@pytest.mark.parametrize('tag,bit', [('APK',30),('ATP',31),('ASL',28)])
def test_a_marker_preserves_low_byte_and_records_transition_side_effect(tag,bit):
    result = decode_client_region_label(tag+'_123', initial_flags=7)
    assert result.flags == (1 << bit) | 7 and result.low_byte == 7
    if tag == 'ATP':
        assert result.transition_write_kind == 'format_numeric_suffix_at_4'
        assert result.transition_source == '123'
    else:
        assert result.transition_write_kind is None


def test_non_a_positional_markers_apply_even_to_unknown_prefix():
    result = decode_client_region_label('XXPTPabc', initial_flags=6)
    assert result.flags == 0xc0000006 and result.matched_prefix is None
    assert result.transition_write_kind == 'copy_complete_label'
    assert result.transition_source == 'XXPTPabc'
    result = decode_client_region_label('AXPTPabc', initial_flags=6)
    assert result.flags == 6 and result.transition_write_kind is None


@pytest.mark.parametrize('last,bit', [('P',27),('F',26)])
def test_long_label_exact_marker_positions(last,bit):
    result = decode_client_region_label('DR'+'_'*29+'MS'+last)
    assert result.flags == (1<<29) | (1<<28) | (1<<bit)
    short = decode_client_region_label('DR'+'_'*29+'MS')
    assert short.flags == (1<<29) | (1<<28)  # byte33 is the C terminator
    assert decode_client_region_label('DR'+'_'*29+'M').flags == 0


def test_a_types_return_before_long_label_markers_and_c_string_stops_at_nul():
    assert decode_client_region_label('AWT'+'_'*28+'MSP').flags == 5
    assert decode_client_region_label(b'WT_Z\x00DRNTP').flags == 5
    assert decode_client_region_label(b'WT\x00_foo', initial_flags=7).flags == 7


@pytest.mark.parametrize('label,flags', [('x'*4097,0),('水',0),(123,0),
                                        ('WT_Z',-1),('WT_Z',True),('WT_Z',1<<32)])
def test_invalid_copied_inputs_refuse(label,flags):
    with pytest.raises(ValueError):
        decode_client_region_label(label, initial_flags=flags)


def test_copied_map_uses_optional_text_name_fallback_and_later_record_precedence():
    mapping = ClientRegionMap(region_wld())
    assert mapping.region_to_record == (-1,0,1)
    assert mapping.flags_for_region(1).flags == 5  # Fragment-name fallback WT_ZONE
    assert mapping.flags_for_region(2).flags == 1 << 31  # Decoded DRNTP overrides name
    absent = mapping.flags_for_region(0, initial_flags=7)
    assert absent.flags == 7 and not absent.label_present and not absent.dry_verified
    overlapped = ClientRegionMap(region_wld(water_id=2))
    assert overlapped.overwrites == ((2,0,1),)
    assert overlapped.flags_for_region(2).flags == 1 << 31


@pytest.mark.parametrize('region', [-1,3,None,True])
def test_missing_child_and_invalid_region_are_not_an_unassigned_valid_region(region):
    with pytest.raises(ValueError):
        ClientRegionMap(region_wld()).flags_for_region(region)


def test_noncontiguous_type_fragments_are_not_silently_renumbered():
    wld = region_wld()
    wld.fragments = (*wld.fragments[:-1], replace(wld.fragments[-1], index=99))
    with pytest.raises(ValueError, match='Noncontiguous'):
        ClientRegionMap(wld)
