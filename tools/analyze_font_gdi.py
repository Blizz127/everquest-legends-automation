#!/usr/bin/env python3
"""Import a pinned isolated GDI result into the private font-model store."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from eql_automation.font_gdi_probe import read_gdi_probe
from eql_automation.font_geometry import (
    command_font_geometry, COPIED_RUNTIME_SHA256, RASTER_RUNTIME_SHA256,
)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--input-sha256',required=True)
    parser.add_argument('--font-sha256',required=True)
    parser.add_argument('--descriptor-sha256',required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--base-height',type=int,
                        help='Optional geometry hypothesis; requires --ui-scale and --client-box-ui')
    parser.add_argument('--ui-scale',type=float)
    parser.add_argument('--client-box-ui',type=int,nargs=4,metavar=('LEFT','TOP','RIGHT','BOTTOM'))
    args=parser.parse_args()
    private=(Path.home()/'.local/share/eql-automation/font-probes').resolve()
    output=args.output.expanduser().resolve()
    if not output.is_relative_to(private) or output==private:
        parser.error('Output must be a new directory below ~/.local/share/eql-automation/font-probes')
    if args.input.stat().st_size>33*1024*1024:parser.error('Probe exceeds size bound')
    geometry_args=(args.base_height,args.ui_scale,args.client_box_ui)
    if any(v is not None for v in geometry_args) and not all(v is not None for v in geometry_args):
        parser.error('Geometry requires --base-height, --ui-scale and --client-box-ui together')
    try:
        probe=read_gdi_probe(args.input.read_bytes(),expected_sha256=args.input_sha256,
                            font_sha256=args.font_sha256,descriptor_sha256=args.descriptor_sha256)
        renderings=probe.prefix_renderings()
        geometry=[]
        if args.base_height is not None:
            from eql_automation.command_text_match import PREFIXES
            for prefix in PREFIXES:
                for caret in (False,True):
                    geometry.append(command_font_geometry(probe,prefix,
                        base_height=args.base_height,ui_scale=args.ui_scale,
                        client_box_ui=tuple(args.client_box_ui),focused=True,caret_visible=caret,
                        eqgame_sha256=COPIED_RUNTIME_SHA256,
                        graphics_sha256=RASTER_RUNTIME_SHA256).summary())
    except ValueError as error:parser.error(str(error))
    output.parent.mkdir(parents=True,exist_ok=True)
    output.mkdir(mode=0o700)
    from PIL import Image
    manifest=probe.summary()
    # PNGs remain the raw alpha4 probe model; geometry is a separate diagnostic.
    manifest['preprojection_geometry']=geometry
    manifest['pngs_apply_geometry']=False
    manifest['renderings']=[]
    for index,t in enumerate(renderings):
        name=f'prefix-{index:02d}.png'
        image=Image.frombytes('RGBA',(t.width,t.height),t.rgba)
        image.save(output/name);(output/name).chmod(0o600)
        manifest['renderings'].append(dict(prefix=t.prefix,variant=t.variant,size=(t.width,t.height),
            image=name,png_sha256=sha256((output/name).read_bytes()).hexdigest(),rgba_sha256=sha256(t.rgba).hexdigest()))
    path=output/'manifest.json';path.write_text(json.dumps(manifest,indent=2)+'\n');path.chmod(0o600)
    print(json.dumps(dict(path=str(path),sha256=sha256(path.read_bytes()).hexdigest(),
        selected_font_sha256=probe.font_sha256,renderings=len(renderings),live_raster_equivalence_verified=False,
        geometry_cases=len(geometry),input_authorized=False)))


if __name__=='__main__':main()
