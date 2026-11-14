"""Ephemeral chat input crops from the frame reader's existing sample.

No capture, saved chat text, OCR or input. Geometry remains a source proposal.
The enclosing frame reader owns pre/post pixel and file-consistency checks;
these regions cannot establish focus, draft ownership or a movement permit.
"""
from dataclasses import dataclass
from hashlib import sha256

from .chat_ui_layout import ChatLayoutUnavailable, resolve_chat_input_geometry
from .owner_ui_observation import UiFrameSample


@dataclass(frozen=True)
class ChatInputFrame:
    geometry: dict
    images: dict
    frame_rgb_sha256: str

    def summary(self):
        """Serializable diagnostic only; images and text stay out of the report."""
        return dict(format='eql-chat-input-frame-v1', status='source_geometry_proposal',
            geometry=self.geometry, frame_rgb_sha256=self.frame_rgb_sha256,
            regions={name:dict(box=self.geometry['pixel_box_proposals'][name],
                              size=list(image.size),rgb_sha256=sha256(image.tobytes()).hexdigest())
                     for name,image in self.images.items()},
            focus='unknown',draft='unknown',active_tab='unknown',
            pixel_values_saved=False,text_recognized=False,game_input_sent=False,
            input_authorized=False)


def chat_regions_from_sample(sample, *, copied_binary_sha256):
    """Use this sample's layout and pixels; never acquire a second frame.

    The supplied UiFrameSample is borrowed within analyze_ui_frame's consistency
    checks. Both returned RGB images are private copies for that feature pass.
    A missing/offscreen region refuses; it is never clipped to an apparent
    empty field. Binary identity denotes inspected copied semantics only.
    """
    if not isinstance(sample,UiFrameSample) or sample.image.mode!='RGB':
        raise ChatLayoutUnavailable('A borrowed RGB frame sample is required')
    if not all(hasattr(sample.layout,name) for name in
               ('elements','sources','skin','ui_scale','screen_for','_window_box','_to_screen')):
        raise ChatLayoutUnavailable('Loaded layout lacks dynamic chat source context')
    geometry=resolve_chat_input_geometry(sample.layout,copied_binary_sha256=copied_binary_sha256)
    if (geometry['saved_skin']!=sample.metadata['ui_skin_from_saved_ini']
            or geometry['saved_scale']!=sample.metadata['ui_scale_from_saved_ini']):
        raise ChatLayoutUnavailable('Chat layout identity changed since sampling')
    for path in geometry['element_source_paths'].values():
        if not path or path not in sample.sources:
            raise ChatLayoutUnavailable('Chat source is absent from this frame source manifest')
    images={}
    for name,box in geometry['pixel_box_proposals'].items():
        if (len(box)!=4 or any(type(v) is not int for v in box)
                or not 0<=box[0]<box[2]<=sample.image.width
                or not 0<=box[1]<box[3]<=sample.image.height):
            raise ChatLayoutUnavailable('Chat input proposal is missing, offscreen or clipped')
        images[name]=sample.image.crop(tuple(box))
    return ChatInputFrame(geometry,images,sample.metadata['frame_rgb_sha256'])
