#!/usr/bin/env python3
"""Import a pinned isolated GDI result into the private font-model store."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from eql_automation.font_gdi_probe import read_gdi_probe, compare_dib_history
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
    parser.add_argument('--diagnostic-only',action='store_true',
                        help='Record probe/DC metadata without building independent glyph PNGs')
    parser.add_argument('--compare-baseline',type=Path,
                        help='Pinned version-2 clear-each probe for a DIB reuse comparison')
    parser.add_argument('--baseline-sha256')
    parser.add_argument('--sample-pixels',action='store_true',
                        help='Apply conditional per-glyph sampling; save RGBA plus unknown-edge masks')
    parser.add_argument('--pixel-box',type=int,nargs=4,metavar=('LEFT','TOP','RIGHT','BOTTOM'))
    parser.add_argument('--screen-offset',type=float,nargs=2)
    parser.add_argument('--text-rgb',type=int,nargs=3)
    parser.add_argument('--text-alpha',type=int)
    parser.add_argument('--pipeline-evidence-sha256')
    args=parser.parse_args()
    private=(Path.home()/'.local/share/eql-automation/font-probes').resolve()
    output=args.output.expanduser().resolve()
    if not output.is_relative_to(private) or output==private:
        parser.error('Output must be a new directory below ~/.local/share/eql-automation/font-probes')
    if args.input.stat().st_size>33*1024*1024:parser.error('Probe exceeds size bound')
    geometry_args=(args.base_height,args.ui_scale,args.client_box_ui)
    if any(v is not None for v in geometry_args) and not all(v is not None for v in geometry_args):
        parser.error('Geometry requires --base-height, --ui-scale and --client-box-ui together')
    if (args.compare_baseline is None)!=(args.baseline_sha256 is None):
        parser.error('--compare-baseline and --baseline-sha256 are required together')
    if args.compare_baseline is not None and not args.diagnostic_only:
        parser.error('DIB history comparison requires --diagnostic-only')
    raster_args=(args.pixel_box,args.screen_offset,args.text_rgb,args.text_alpha,args.pipeline_evidence_sha256)
    if args.sample_pixels:
        if not all(v is not None for v in (*geometry_args,*raster_args)) or args.diagnostic_only:
            parser.error('Sampling requires geometry, pixel box, offset, tint and pipeline evidence; no diagnostic-only')
    elif any(v is not None for v in raster_args):
        parser.error('Pixel-model options require --sample-pixels')
    try:
        probe=read_gdi_probe(args.input.read_bytes(),expected_sha256=args.input_sha256,
                            font_sha256=args.font_sha256,descriptor_sha256=args.descriptor_sha256)
        renderings=() if args.diagnostic_only else probe.prefix_renderings()
        comparison=None
        if args.compare_baseline is not None:
            if args.compare_baseline.stat().st_size>33*1024*1024:
                raise ValueError('Baseline probe exceeds size bound')
            baseline=read_gdi_probe(args.compare_baseline.read_bytes(),expected_sha256=args.baseline_sha256,
                                   font_sha256=args.font_sha256,descriptor_sha256=args.descriptor_sha256)
            comparison=compare_dib_history(baseline,probe)
        geometry=[];sampled=[]
        if args.base_height is not None:
            from eql_automation.command_text_match import PREFIXES
            for prefix in PREFIXES:
                for caret in (False,True):
                    modeled=command_font_geometry(probe,prefix,
                        base_height=args.base_height,ui_scale=args.ui_scale,
                        client_box_ui=tuple(args.client_box_ui),focused=True,caret_visible=caret,
                        eqgame_sha256=COPIED_RUNTIME_SHA256,
                        graphics_sha256=RASTER_RUNTIME_SHA256)
                    geometry.append(modeled.summary())
                    if args.sample_pixels:
                        from eql_automation.font_raster import sample_command_font
                        sampled.append(sample_command_font(probe,modeled,
                            pixel_box=tuple(args.pixel_box),screen_offset=tuple(args.screen_offset),
                            text_rgb=tuple(args.text_rgb),text_alpha=args.text_alpha,
                            pipeline_evidence_sha256=args.pipeline_evidence_sha256))
    except ValueError as error:parser.error(str(error))
    output.parent.mkdir(parents=True,exist_ok=True)
    output.mkdir(mode=0o700)
    from PIL import Image
    manifest=probe.summary()
    # Legacy prefix PNGs remain raw. Sampled images/masks are stored separately.
    manifest['preprojection_geometry']=geometry
    manifest['pngs_apply_geometry']=False
    manifest['dib_history_comparison']=comparison
    manifest['renderings']=[]
    for index,t in enumerate(renderings):
        name=f'prefix-{index:02d}.png'
        image=Image.frombytes('RGBA',(t.width,t.height),t.rgba)
        image.save(output/name);(output/name).chmod(0o600)
        manifest['renderings'].append(dict(prefix=t.prefix,variant=t.variant,size=(t.width,t.height),
            image=name,png_sha256=sha256((output/name).read_bytes()).hexdigest(),rgba_sha256=sha256(t.rgba).hexdigest()))
    manifest['sampled_renderings']=[]
    if sampled:
        manifest['sampling_code_sha256']={name:sha256((Path(__file__).resolve().parents[1]/
            'eql_automation'/name).read_bytes()).hexdigest() for name in
            ('font_geometry.py','font_raster.py','command_text_match.py')}
    for index,result in enumerate(sampled):
        t=result.rendering
        rgba_name=f'sampled-{index:02d}.png';mask_name=f'sampled-known-{index:02d}.png'
        Image.frombytes('RGBA',(t.width,t.height),t.rgba).save(output/rgba_name)
        Image.frombytes('L',(t.width,t.height),t.known_pixels).save(output/mask_name)
        (output/rgba_name).chmod(0o600);(output/mask_name).chmod(0o600)
        manifest['sampled_renderings'].append(dict(result.summary(),image=rgba_name,known_mask=mask_name,
            png_sha256=sha256((output/rgba_name).read_bytes()).hexdigest(),
            mask_png_sha256=sha256((output/mask_name).read_bytes()).hexdigest()))
    path=output/'manifest.json';path.write_text(json.dumps(manifest,indent=2)+'\n');path.chmod(0o600)
    print(json.dumps(dict(path=str(path),sha256=sha256(path.read_bytes()).hexdigest(),
        selected_font_sha256=probe.font_sha256,renderings=len(renderings),live_raster_equivalence_verified=False,
        geometry_cases=len(geometry),sampled_cases=len(sampled),input_authorized=False)))


if __name__=='__main__':main()
