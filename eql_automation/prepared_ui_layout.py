"""Prepare the retained UI parser once; recheck all inputs for each frame.

The include manifest and losing/empty includes are dependencies too. File
selection is resolved again on each check, so newly added skin/variant files
cannot silently reuse an old parse. No display, input or filesystem writes.
"""
from configparser import RawConfigParser
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import time
from types import MappingProxyType
import xml.etree.ElementTree as ET


@dataclass(frozen=True)
class PreparedLayoutView:
    layout: object
    source_hashes: object
    source_verifier: object
    preparation: object

    def __getattr__(self, name):
        return getattr(self.layout,name)


class PreparedUiLayout:
    """A callable replacement for UiLayout.load in one prepared reader.

    Every use returns a new layout/cache and INI copy. Parsed XML elements
    remain trusted, borrowed, read-only objects, just as UiFrameSample's layout.
    Source or binding changes refuse; reparsing is not hidden inside a frame.
    """
    def __init__(self, layout_type, *, game, character, server, width, height,
                 clock=time.monotonic):
        if (not callable(getattr(layout_type,'load',None)) or not callable(clock)
                or any(type(v) is not int or not 1<=v<=16384 for v in (width,height))
                or not all(isinstance(v,str) and re.fullmatch(r'[A-Za-z0-9_-]{1,64}',v)
                           for v in (character,server))):
            raise ValueError('Bound retained layout type, identifiers and dimensions required')
        self.game=Path(game).resolve()
        self.character,self.server,self.width,self.height=character,server,width,height
        self.layout_type=layout_type
        began=clock()
        before=self._snapshot()
        self._template=layout_type.load(self.game,character,server,width=width,height=height)
        after=self._snapshot()
        if before!=after:
            raise RuntimeError('Client UI sources changed during layout preparation')
        if any(str(p) not in after['files'] for p in self._template.sources.values()):
            raise RuntimeError('Layout parser used an untracked source file')
        self._fingerprint=after
        finished=clock()
        if not all(type(v) in (int,float) and math.isfinite(v) for v in (began,finished)) or finished<began:
            raise ValueError('Invalid layout preparation clock')
        self.preparation=dict(format='eql-prepared-ui-layout-v1',started_at=began,finished_at=finished,
            seconds=finished-began,source_file_count=len(after['files']),
            fingerprint_sha256=sha256(json.dumps(after,sort_keys=True).encode()).hexdigest(),
            game_capture_used=False,game_input_sent=False,contains_scene_observation=False)

    def _snapshot(self):
        files={}
        candidates=[]
        def safe(path):
            resolved=path.resolve()
            if not resolved.is_relative_to(self.game):
                raise ValueError('UI source path leaves the bound game directory')
            return resolved
        def probe(path):
            resolved=safe(path)
            is_file=path.is_file()
            candidates.append((str(path),str(resolved),is_file))
            return is_file
        def read(path):
            safe(path)
            data=path.read_bytes()
            files[str(path)]=sha256(data).hexdigest()
            return data
        def parse_xml(data):
            # Same trailing-document fallback as the retained _parse.
            try:return ET.fromstring(data)
            except ET.ParseError:
                text=data.decode('utf-8',errors='replace');end=text.find('</XML>')
                if end<0:raise
                return ET.fromstring(text[:end+len('</XML>')])
        ini_path=self.game/f'UI_{self.character}_{self.server}.ini'
        suffixes=()
        if not probe(ini_path):
            matches=sorted(self.game.glob(f'UI_{self.character}_{self.server}_*.ini'))
            suffixes=tuple(str(p) for p in matches)
            if len(matches)!=1:raise RuntimeError('Missing or ambiguous character UI INI')
            ini_path=matches[0]
        ini=RawConfigParser(strict=False,interpolation=None);ini.optionxform=str
        ini.read_string(read(ini_path).decode('utf-8',errors='replace'))
        client=self.game/'eqclient.ini'
        if probe(client):read(client)
        skin=ini.get('Main','UISkin',fallback='default') or 'default'
        default=self.game/'uifiles/default';selected=self.game/'uifiles'/skin
        safe(default);safe(selected)
        directory_state=(str(safe(default)),default.is_dir(),str(safe(selected)),selected.is_dir())
        if not default.is_dir():raise RuntimeError('Default UI directory is missing')
        skin_dir=selected if selected.is_dir() else default
        includes=None
        for directory in (skin_dir,default):
            manifest=directory/'EQUI.xml'
            if probe(manifest):
                root=parse_xml(read(manifest))
                names=[node.text.strip() for node in root.iter('Include') if node.text]
                if names:includes=names;break
        if not includes:raise RuntimeError('Missing or empty UI include list')
        variants={}
        for section in ('Default','default'):
            if ini.has_section(section):
                for name,value in ini.items(section):
                    try:variants[name]=int(value)
                    except ValueError:pass
        selections=[]
        for name in includes:
            stem=name[:-4] if name.lower().endswith('.xml') else name
            window=stem[5:] if stem.startswith('EQUI_') else None
            variant=variants.get(window,0) if window else 0
            names=([f'{stem}{variant}.xml'] if variant else [])+[name]
            chosen=None
            for candidate in names:
                for directory in (skin_dir,default):
                    path=directory/candidate
                    if probe(path):chosen=path;break
                if chosen is not None:break
            selections.append((name,None if chosen is None else str(chosen)))
            if chosen is not None:read(chosen)
        return dict(files=files,candidates=candidates,suffix_matches=suffixes,
                    directories=directory_state,skin=skin,includes=includes,selections=selections)

    def verify_sources(self):
        current=self._snapshot()
        if current!=self._fingerprint:
            raise RuntimeError('Prepared client UI source selection or content changed')
        return dict(current['files'])

    def __call__(self, game, character, server, *, width, height):
        if (Path(game).resolve(),character,server,width,height)!=(
                self.game,self.character,self.server,self.width,self.height):
            raise RuntimeError('Prepared UI layout binding or resolution changed')
        sources=self.verify_sources()
        base=self._template
        layout=self.layout_type(elements=dict(base.elements),ini=deepcopy(base.ini),
            width=self.width,height=self.height,ui_scale=base.ui_scale,skin=base.skin,
            sources=dict(base.sources))
        return PreparedLayoutView(layout,MappingProxyType(sources),self.verify_sources,
                                  MappingProxyType(dict(self.preparation)))
