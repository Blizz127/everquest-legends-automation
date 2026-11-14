"""Source-derived chat input geometry, never an observation of chat focus.

The retained UiLayout cannot walk the Page/ChatWindow nodes the client creates
at runtime. This resolver adds that specific hierarchy without changing the
retained loader or guessing the font-dependent tab height. Pixel projection
still uses that loader's unverified scaling/rounding model.
"""
from dataclasses import dataclass, asdict
from hashlib import sha256
import math
import xml.etree.ElementTree as ET


COPIED_RUNTIME_SHA256 = 'fe41a8db0b2cc2dc8848d82dce41d3f94cb6aa86d2aac21aa774efab7146bf36'


class ChatLayoutUnavailable(ValueError):
    pass


@dataclass(frozen=True)
class Edges:
    left: float | None
    top: float | None
    right: float | None
    bottom: float | None

    def inset(self, left, top, right, bottom):
        return Edges(_offset(self.left, left), _offset(self.top, top),
                     _offset(self.right, -right), _offset(self.bottom, -bottom))


def _offset(value, amount):
    return None if value is None else value + amount


def _text(element, path, default=None):
    value = element.findtext(path)
    return default if value is None or not value.strip() else value.strip()


def _number(element, path, default=0):
    raw = _text(element, path)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ChatLayoutUnavailable(f'Invalid integer {element.get("item")}/{path}') from None
    return value


def _bool(element, path, default=False):
    raw = _text(element, path)
    return default if raw is None else raw == 'true'


class _Source:
    def __init__(self, elements):
        self.elements = elements
        self.used = {}

    def get(self, name, tags):
        element = self.elements.get(name)
        if element is None or element.tag not in tags:
            raise ChatLayoutUnavailable(f'Missing or unsupported source element: {name}')
        self.used[name] = sha256(ET.tostring(element)).hexdigest()
        return element

    def size(self, frame, piece):
        name = _text(frame, piece)
        if name is None:
            return (0, 0)  # An absent piece is the native null-animation case.
        animation = self.get(name, ('Ui2DAnimation',))
        frames = animation.findall('Frames')
        if len(frames) != 1:
            raise ChatLayoutUnavailable(f'Animation size needs a single source frame: {name}')
        size = tuple(_number(frames[0], 'Size/' + axis, None) for axis in ('CX', 'CY'))
        if any(value is None or not 0 <= value <= 16384 for value in size):
            raise ChatLayoutUnavailable(f'Missing or invalid frame dimensions: {name}')
        return size

    def frame(self, name, *, window=False):
        element = self.get(name, ('WindowDrawTemplate',) if window else ('FrameTemplate',))
        if not window:
            return element
        border = element.find('Border')
        if border is None:
            raise ChatLayoutUnavailable(f'Missing source Border: {name}')
        return border

    def insets(self, name):
        frame = self.frame(name, window=True)
        # eqgame 0x140628950: each edge uses its three corresponding pieces.
        # Overlap is subtracted after max(..., 0); negative insets are legal.
        edges = (('Left', ('LeftTop', 'Left', 'LeftBottom'), 0),
                 ('Top', ('TopLeft', 'Top', 'TopRight'), 1),
                 ('Right', ('RightTop', 'Right', 'RightBottom'), 0),
                 ('Bottom', ('BottomLeft', 'Bottom', 'BottomRight'), 1))
        return tuple(max(0, *(self.size(frame, piece)[axis] for piece in pieces))
                     - _number(frame, 'Overlap' + edge) for edge, pieces, axis in edges)


def _client(source, element, outer, *, force_border=False):
    # These styles need additional runtime geometry that is not modelled here.
    if any(_bool(element, flag) for flag in ('Style_Titlebar', 'Style_VScroll', 'Style_HScroll')):
        raise ChatLayoutUnavailable(f'Unsupported title/scroll geometry: {element.get("item")}')
    if force_border or _bool(element, 'Style_Border'):
        return outer.inset(*source.insets(_text(element, 'DrawTemplate')))
    return outer


def _anchor(element, parent):
    if not _bool(element, 'RelativePosition', True) or not _bool(element, 'AutoStretch'):
        raise ChatLayoutUnavailable(f'Expected relative stretched child: {element.get("item")}')
    values = []
    for side, flag, near, far in (
            ('Left', 'LeftAnchorToLeft', parent.left, parent.right),
            ('Top', 'TopAnchorToTop', parent.top, parent.bottom),
            ('Right', 'RightAnchorToLeft', parent.left, parent.right),
            ('Bottom', 'BottomAnchorToTop', parent.top, parent.bottom)):
        offset = _number(element, side + 'AnchorOffset')
        values.append(_offset(near, offset) if _bool(element, flag, True) else _offset(far, -offset))
    return Edges(*values)


def _complete(box):
    values = tuple(asdict(box).values())
    if any(type(value) not in (int, float) or not math.isfinite(value) for value in values):
        raise ChatLayoutUnavailable('Input geometry depends on unresolved runtime tab height')
    if box.left >= box.right or box.top >= box.bottom:
        raise ChatLayoutUnavailable('Input geometry has no positive area')
    return box


def resolve_chat_input_geometry(layout, *, copied_binary_sha256, window='MainChat'):
    """Resolve a saved container's proposed input outer/client boxes, read-only.

    `layout` is the retained UiLayout. The binary hash selects static semantics;
    it does not claim a running-process binding. Active tab, visibility, focus,
    clipping, saved placement and final pixel rounding remain unverified.
    No caller may turn an empty proposed crop into a chat-closed permission.
    """
    if copied_binary_sha256 != COPIED_RUNTIME_SHA256:
        raise ChatLayoutUnavailable('Dynamic chat semantics need the inspected copied binary')
    if type(layout.ui_scale) not in (int, float) or not math.isfinite(layout.ui_scale) or layout.ui_scale <= 0:
        raise ChatLayoutUnavailable('Invalid saved UI scale')
    source = _Source(layout.elements)
    container = source.get('ChatContainerWindow', ('Screen',))
    if layout.screen_for(window) is not container:
        raise ChatLayoutUnavailable('Saved window is not the chat container')
    outer = layout._window_box(window)
    if outer is None:
        raise ChatLayoutUnavailable('No saved chat container geometry')
    outer = _complete(Edges(outer.left, outer.top, outer.right, outer.bottom))
    pieces = {_text_value.text.strip().split(':')[-1] for _text_value in container.findall('Pieces') if _text_value.text}
    if not {'CCW_ChatWindows', 'CCW_ChatPageTemplate'} <= pieces:
        raise ChatLayoutUnavailable('Dynamic chat source hierarchy changed')
    tab = source.get('CCW_ChatWindows', ('TabBox',))
    page = source.get('CCW_ChatPageTemplate', ('Page',))
    chat = source.get('ChatWindow', ('Screen',))
    edit = source.get('CW_ChatInput', ('Editbox',))
    if not any((piece.text or '').strip().split(':')[-1] == 'CW_ChatInput' for piece in chat.findall('Pieces')):
        raise ChatLayoutUnavailable('ChatWindow no longer contains its input')
    tab_outer = _anchor(tab, _client(source, container, outer))
    tab_client = _client(source, tab, tab_outer)
    frame = source.frame(_text(tab, 'PageBorderTemplate'))
    # Native page layout 0x140622320 uses these exact corner slots, not
    # general frame maxima. Page top also needs the runtime font/tab height.
    left = source.size(frame, 'LeftTop')[0]
    right = source.size(frame, 'RightTop')[0]
    bottom = source.size(frame, 'Bottom')[1]
    top = source.size(frame, 'Top')[1]
    tab_frame = source.frame(_text(tab, 'TabBorderTemplate'))
    top_offset = top - source.size(tab_frame, 'LeftBottom')[1]
    page_top = None if _bool(tab, 'ShowTabs', True) else _offset(tab_client.top, top_offset)
    page_outer = Edges(_offset(tab_client.left, left), page_top,
                       _offset(tab_client.right, -right), _offset(tab_client.bottom, -bottom))
    chat_outer = _anchor(chat, _client(source, page, page_outer))
    edit_outer = _complete(_anchor(edit, _client(source, chat, chat_outer)))
    # ChatWindow ctor 0x1403d7c89 adds 0xc0, including border bit 0x40,
    # even when the input XML's Style_Border is false.
    edit_client = _complete(_client(source, edit, edit_outer, force_border=True))
    projected = {}
    for name, box in (('outer', edit_outer), ('client', edit_client)):
        rect = layout._to_screen(box)
        projected[name] = [rect.x, rect.y, rect.x + rect.w, rect.y + rect.h]
    return dict(format='eql-chat-input-geometry-v1',window=window,saved_skin=layout.skin,
        saved_scale=layout.ui_scale,copied_binary_sha256=copied_binary_sha256,
        ui_units={'container':asdict(outer),'tab_client':asdict(tab_client),
                  'page':asdict(page_outer),'chat':asdict(chat_outer),
                  'input_outer':asdict(edit_outer),'input_client':asdict(edit_client)},
        page_top_formula=dict(runtime_tab_height_required=_bool(tab,'ShowTabs',True),
                              offset_from_tab_client_top=top_offset),
        input_border_forced_by_runtime=True,pixel_box_proposals=projected,
        parsed_element_sha256=dict(source.used),
        element_source_paths={name:str(layout.sources.get(name,'')) for name in source.used},
        active_tab='unknown',chat_focus='unknown',chat_draft='unknown',
        runtime_clipping_verified=False,scaling_rounding_verified=False,
        saved_layout_live_verified=False,active_runtime_binary_verified=False,
        game_capture_used=False,game_input_sent=False,input_authorized=False)
