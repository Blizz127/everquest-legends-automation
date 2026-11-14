from copy import deepcopy
from types import SimpleNamespace
import xml.etree.ElementTree as ET

import pytest

from eql_automation.chat_ui_layout import (
    COPIED_RUNTIME_SHA256, ChatLayoutUnavailable, Edges, resolve_chat_input_geometry,
)


def element(tag, name, body=''):
    return ET.fromstring(f'<{tag} item="{name}">{body}</{tag}>')


@pytest.fixture
def layout():
    elements = {}
    def add(tag, name, body=''):
        elements[name] = element(tag, name, body)
        return elements[name]
    def animation(name, width, height):
        add('Ui2DAnimation', name, f'<Frames><Size><CX>{width}</CX><CY>{height}</CY></Size></Frames>')
    def border(name, sizes, overlaps=''):
        refs = ''
        for piece, size in sizes.items():
            key = name + piece
            animation(key, *size)
            refs += f'<{piece}>{key}</{piece}>'
        add('WindowDrawTemplate', name, '<Border>' + refs + overlaps + '</Border>')
    fill = ('<RelativePosition>true</RelativePosition><AutoStretch>true</AutoStretch>'
            '<RightAnchorToLeft>false</RightAnchorToLeft><BottomAnchorToTop>false</BottomAnchorToTop>')
    add('Screen', 'ChatContainerWindow', '<Style_Border>true</Style_Border><DrawTemplate>container</DrawTemplate>'
        '<Pieces>CCW_ChatWindows</Pieces><Pieces>CCW_ChatPageTemplate</Pieces>')
    border('container', {'Left':(2,1),'Top':(1,3),'Right':(5,1),'Bottom':(1,7)})
    add('TabBox','CCW_ChatWindows',fill + '<TopAnchorOffset>1</TopAnchorOffset>'
        '<PageBorderTemplate>page</PageBorderTemplate><TabBorderTemplate>tab</TabBorderTemplate>')
    add('Page','CCW_ChatPageTemplate','<DrawTemplate>unused-page-border</DrawTemplate>')
    # Deliberately unequal middle/corner sizes: page layout uses LeftTop and
    # RightTop directly, not general border maxima or middle-side dimensions.
    add('FrameTemplate','page','<LeftTop>page-left</LeftTop><Left>page-middle</Left>'
        '<RightTop>page-right</RightTop><Top>page-top</Top><Bottom>page-bottom</Bottom>')
    for name,size in {'page-left':(4,2),'page-middle':(99,99),'page-right':(6,3),
                      'page-top':(1,5),'page-bottom':(1,8),'tab-bottom':(2,3)}.items():
        animation(name,*size)
    add('FrameTemplate','tab','<LeftBottom>tab-bottom</LeftBottom>')
    add('Screen','ChatWindow',fill+'<Style_Border>true</Style_Border>'
        '<DrawTemplate>chat</DrawTemplate><Pieces>CW_ChatInput</Pieces>')
    border('chat', {'Left':(21,1),'Top':(1,10),'Right':(35,1),'Bottom':(1,7)},
           '<OverlapRight>35</OverlapRight>')
    add('Editbox','CW_ChatInput',fill+'<TopAnchorToTop>false</TopAnchorToTop>'
        '<TopAnchorOffset>21</TopAnchorOffset><RightAnchorOffset>35</RightAnchorOffset>'
        '<DrawTemplate>input</DrawTemplate><Style_Border>false</Style_Border>')
    border('input',{'Left':(21,1),'Right':(21,1)})
    def pixels(box):
        # Fixture-only projection, not a claim about runtime rounding.
        l,t,r,b = (round(v*1.25) for v in (box.left,box.top,box.right,box.bottom))
        return SimpleNamespace(x=l,y=t,w=r-l,h=b-t)
    return SimpleNamespace(elements=elements,sources={},skin='fixture',ui_scale=1.25,
        screen_for=lambda name:elements['ChatContainerWindow'],
        _window_box=lambda name:Edges(100,200,700,500),_to_screen=pixels)


def resolve(layout, **kwargs):
    return resolve_chat_input_geometry(layout,copied_binary_sha256=COPIED_RUNTIME_SHA256,**kwargs)


def change(layout,name,path,value):
    node=layout.elements[name].find(path)
    if node is None:node=ET.SubElement(layout.elements[name],path)
    node.text=value


def test_dynamic_pages_resolve_bottom_input_without_fabricating_tab_height(layout):
    before={k:ET.tostring(v) for k,v in layout.elements.items()}
    result=resolve(layout)
    assert result['ui_units']['page']==dict(left=106,top=None,right=689,bottom=485)
    assert result['ui_units']['input_outer']==dict(left=127,top=457,right=654,bottom=478)
    # The constructor's border override must be applied despite XML false.
    assert result['ui_units']['input_client']==dict(left=148,top=457,right=633,bottom=478)
    assert result['page_top_formula']==dict(runtime_tab_height_required=True,offset_from_tab_client_top=2)
    assert 'page-middle' not in result['parsed_element_sha256']
    assert before=={k:ET.tostring(v) for k,v in layout.elements.items()}
    assert result['chat_focus']==result['chat_draft']==result['active_tab']=='unknown'
    assert not any(result[k] for k in ('input_authorized','game_input_sent','game_capture_used',
        'saved_layout_live_verified','scaling_rounding_verified','runtime_clipping_verified'))


def test_overlap_larger_than_art_is_not_clamped(layout):
    change(layout,'chat','Border/OverlapRight','40')
    assert resolve(layout)['ui_units']['input_outer']['right']==659


def test_general_border_uses_corner_maxima_on_correct_axis(layout):
    e=layout.elements
    e['corner']=element('Ui2DAnimation','corner','<Frames><Size><CX>29</CX><CY>77</CY></Size></Frames>')
    ET.SubElement(e['chat'].find('Border'),'LeftBottom').text='corner'
    # LeftBottom affects left width; it is not a BottomLeft piece and must
    # not move the bottom by 77.
    result=resolve(layout)['ui_units']['input_outer']
    assert result==dict(left=135,top=457,right=654,bottom=478)


@pytest.mark.parametrize('piece',['BottomLeft','BottomRight'])
def test_bottom_uses_corner_height(layout,piece):
    layout.elements['corner']=element('Ui2DAnimation','corner','<Frames><Size><CX>1</CX><CY>11</CY></Size></Frames>')
    ET.SubElement(layout.elements['chat'].find('Border'),piece).text='corner'
    assert resolve(layout)['ui_units']['input_outer']['bottom']==474


def test_unknown_top_is_propagated_when_input_depends_on_it(layout):
    change(layout,'CW_ChatInput','TopAnchorToTop','true')
    with pytest.raises(ChatLayoutUnavailable,match='tab height'):resolve(layout)
    change(layout,'CCW_ChatWindows','ShowTabs','false')
    result=resolve(layout)
    assert result['ui_units']['page']['top']==206
    assert result['ui_units']['input_outer']['top']==237


@pytest.mark.parametrize('mutation',['missing-animation','missing-template','missing-dimension',
    'multiple-frames','negative-size','scroll-style','changed-hierarchy','non-stretched','zero-area'])
def test_incomplete_or_unsupported_sources_refuse_instead_of_zero_insets(layout,mutation):
    if mutation=='missing-animation':del layout.elements['containerLeft']
    elif mutation=='missing-template':del layout.elements['input']
    elif mutation=='missing-dimension':layout.elements['containerLeft'].find('Frames/Size').remove(layout.elements['containerLeft'].find('Frames/Size/CX'))
    elif mutation=='multiple-frames':layout.elements['containerLeft'].append(deepcopy(layout.elements['containerLeft'].find('Frames')))
    elif mutation=='negative-size':change(layout,'containerLeft','Frames/Size/CX','-1')
    elif mutation=='scroll-style':change(layout,'ChatWindow','Style_VScroll','true')
    elif mutation=='changed-hierarchy':layout.elements['ChatWindow'].remove(layout.elements['ChatWindow'].find('Pieces'))
    elif mutation=='non-stretched':change(layout,'CW_ChatInput','AutoStretch','false')
    elif mutation=='zero-area':change(layout,'CW_ChatInput','RightAnchorOffset','9999')
    with pytest.raises(ChatLayoutUnavailable):resolve(layout)


def test_binary_and_saved_geometry_are_required(layout):
    with pytest.raises(ChatLayoutUnavailable,match='binary'):
        resolve_chat_input_geometry(layout,copied_binary_sha256='0'*64)
    layout._window_box=lambda name:None
    with pytest.raises(ChatLayoutUnavailable,match='saved'):resolve(layout)


def test_page_border_is_not_inset_twice(layout):
    # Fresh Page defaults to no window border; the dangling unused template
    # intentionally is absent. Native PageBorder sizing already consumed it.
    assert resolve(layout)['ui_units']['chat']['bottom']==485
    change(layout,'CCW_ChatPageTemplate','Style_Border','true')
    with pytest.raises(ChatLayoutUnavailable,match='source element'):resolve(layout)
