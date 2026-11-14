"""Read the visible actor-zone footer and compare its coordinates to fresh /loc.

No fuzzy catalog matching, old screenshots, input, or navigation positions.
Only the pinned client build/layout semantics are supported by this adapter.
"""
from dataclasses import dataclass, asdict
from hashlib import sha256
import csv
import io
import math
from pathlib import Path
import re
import subprocess
import time

from PIL import Image, ImageOps, ImageStat

from .location_log import unique_client_zone_ids
from .owner_ui_observation import sample_focused_ui, file_sha
from .unbound_location_log import UnboundLocationObservation

EXE_PIN = 'fe41a8db0b2cc2dc8848d82dce41d3f94cb6aa86d2aac21aa774efab7146bf36'
XML_PIN = '6bcdcc7b20c6510c5797e044ab3193b8a7fa2386dc87e8d770b5387346fe6419'
CONTROL_TYPES = (('MRA_ZoneLabel', 1020), ('MRA_LocXCoords', 1021),
                 ('MRA_LocYCoords', 1022), ('MRA_LocZCoords', 1023))
MAP_CONTROLS = tuple(('MapViewWnd', name) for name, _ in CONTROL_TYPES)
OCR_ROOT = Path.home()/'.local/share/eql-automation/tools/tesseract-5.5.0-linux64'


def read_tsv_line(text):
    rows = list(csv.DictReader(io.StringIO(text), delimiter='\t'))
    words = [r for r in rows if r.get('level') == '5' and r.get('text', '').strip()]
    if not words or len(words) > 24:
        raise ValueError('Map text was not recognized')
    lines = {(r['page_num'], r['block_num'], r['par_num'], r['line_num']) for r in words}
    scores = [float(r['conf']) for r in words]
    if len(lines) != 1 or any(not math.isfinite(v) or v < 85 for v in scores):
        raise ValueError('Map text is unclear or has multiple lines')
    return ' '.join(r['text'].strip() for r in words), min(scores)


class TesseractLineReader:
    def __init__(self, executable=None):
        self.executable = Path(executable or OCR_ROOT/'run')
        if not self.executable.is_file():
            raise ValueError('Private map OCR tool is unavailable')

    def __call__(self, image):
        if not isinstance(image, Image.Image) or not 8 <= image.width <= 1024 or not 6 <= image.height <= 128:
            raise ValueError('Map label crop is missing or outside supported dimensions')
        gray = ImageOps.grayscale(image)
        if ImageStat.Stat(gray).stddev[0] < 8:
            raise ValueError('Map label is blank; open the map before the hotbutton test')
        if ImageStat.Stat(gray).mean[0] < 128:
            gray = ImageOps.invert(gray)
        gray = ImageOps.autocontrast(gray)
        # Long label rectangles leave tiny numeric strings surrounded by blank
        # pixels. Trim that padding, then give every line the same quiet border.
        ink = ImageOps.invert(gray).point(lambda value: 255 if value > 32 else 0).getbbox()
        if ink is None:
            raise ValueError('Map label contains no text')
        gray = gray.crop(ink)
        gray = gray.resize((gray.width*3, gray.height*3), Image.Resampling.LANCZOS)
        gray = ImageOps.expand(gray, border=12, fill=255)
        stream = io.BytesIO(); gray.save(stream, format='PNG')
        result = subprocess.run([str(self.executable), 'stdin', 'stdout', '-l', 'eng', '--psm', '7', 'tsv'],
            input=stream.getvalue(), capture_output=True, timeout=1.5, check=True)
        if len(result.stdout) > 65536:
            raise ValueError('Map OCR output exceeded its bound')
        text, confidence = read_tsv_line(result.stdout.decode('utf-8'))
        return dict(text=text, confidence=confidence, crop_sha256=sha256(image.tobytes()).hexdigest())


@dataclass(frozen=True)
class MapZoneObservation:
    zone_id: int
    zone_name: str
    displayed_coordinates: tuple[float, float, float]
    raw_coordinates: tuple[float, float, float]
    capture_started_at: float
    checked_at: float
    frame_sha256: str
    window_id: int
    process: tuple[int, int]
    catalog_sha256: str
    texts: tuple[str, str, str, str]

    def record(self):
        return dict(asdict(self), source='map_label_with_fresh_location',
            map_coordinates_are_navigation_input=False, game_input_sent=False)


def read_current_map_zone(*, gate, layout_loader, game, character, server, fix,
                          line_reader, still_current, clock=time.monotonic):
    game = Path(game)
    if not isinstance(fix, UnboundLocationObservation) or not 0 <= clock()-fix.received_monotonic <= 2.5:
        raise ValueError('Map recognition requires the current hotbutton reply')
    still_current()
    if file_sha(game/'eqgame.exe') != EXE_PIN:
        raise ValueError('Current client build differs from the inspected map-label semantics')
    catalog = game/'Resources/ZoneNames.txt'
    catalog_pin = file_sha(catalog)
    zones, _ = unique_client_zone_ids(catalog)
    sample = sample_focused_ui(gate=gate, layout_loader=layout_loader, game=game,
        character=character, server=server, still_current=still_current, clock=clock,
        controls=MAP_CONTROLS, required_control='MapViewWnd__MRA_ZoneLabel')
    if sample.metadata['capture_started_monotonic'] < fix.received_monotonic:
        raise ValueError('Map capture predates the location reply')
    rows = []
    for name, kind in CONTROL_TYPES:
        still_current()
        source = sample.layout.sources.get(name)
        element = sample.layout.elements.get(name)
        if (source is None or sample.sources.get(str(source)) != XML_PIN
                or element is None or element.findtext('EQType') != str(kind)):
            raise ValueError('Map label source or EQType changed')
        box = sample.boxes.get('MapViewWnd__'+name)
        if box is None:
            raise ValueError('Map footer is offscreen or unavailable')
        row = line_reader(sample.image.crop(box))
        confidence = row.get('confidence')
        if (not isinstance(row.get('text'), str) or isinstance(confidence, bool)
                or not isinstance(confidence, (float, int))
                or not math.isfinite(confidence) or not 85 <= confidence <= 100):
            raise ValueError('Map text recognition is unclear')
        rows.append(row)
    name = rows[0]['text']
    if name not in zones or name == 'Unknown Zone':
        raise ValueError('Map zone text does not exactly match a unique client zone')
    numbers = []
    for row in rows[1:]:
        if not re.fullmatch(r'-?\d{1,7}', row['text']):
            raise ValueError('Map coordinates are not complete integer labels')
        numbers.append(float(row['text']))
    # Native 1021/1022/1023 read +74/+78/+7c in the SAME order as /location,
    # despite conventional Y/X axis names. %.0f versus %1.2f permits .505.
    if any(abs(a-b) > .50500001 for a, b in zip(numbers, fix.raw_coordinates)):
        raise ValueError('Visible map coordinates disagree with the fresh location reply')
    sample.check_sources(); still_current()
    if file_sha(catalog) != catalog_pin or file_sha(game/'eqgame.exe') != EXE_PIN:
        raise ValueError('Client map observation sources changed')
    finished = clock()
    if not 0 <= finished-fix.received_monotonic <= 2.5:
        raise ValueError('Map recognition exceeded the fresh reply interval')
    session = sample.metadata['game_session']
    return MapZoneObservation(zones[name], name, tuple(numbers), fix.raw_coordinates,
        sample.metadata['capture_started_monotonic'], finished,
        sample.metadata['frame_rgb_sha256'], sample.metadata['focused_window_id'],
        (session['pid'], int(session['start_ticks'])), catalog_pin,
        tuple(row['text'] for row in rows))


def observe_owner_map_zone(engine, pending, *, still_current):
    from uilayout import UiLayout
    return read_current_map_zone(gate=engine.gate, layout_loader=UiLayout.load,
        game=engine.settings.game_dir, character=engine.settings.character,
        server=engine.settings.server, fix=pending['fix'],
        line_reader=TesseractLineReader(), still_current=still_current)
