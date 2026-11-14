#!/usr/bin/env python3
"""Import a pinned isolated GDI result into the private font-model store."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from eql_automation.font_gdi_probe import read_gdi_probe


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--input-sha256',required=True)
    parser.add_argument('--font-sha256',required=True)
    parser.add_argument('--descriptor-sha256',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    private=(Path.home()/'.local/share/eql-automation/font-probes').resolve()
    output=args.output.expanduser().resolve()
    if not output.is_relative_to(private) or output==private:
        parser.error('Output must be a new directory below ~/.local/share/eql-automation/font-probes')
    if args.input.stat().st_size>33*1024*1024:parser.error('Probe exceeds size bound')
    try:
        probe=read_gdi_probe(args.input.read_bytes(),expected_sha256=args.input_sha256,
                            font_sha256=args.font_sha256,descriptor_sha256=args.descriptor_sha256)
        renderings=probe.prefix_renderings()
    except ValueError as error:parser.error(str(error))
    output.parent.mkdir(parents=True,exist_ok=True)
    output.mkdir(mode=0o700)
    from PIL import Image
    manifest=probe.summary()
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
        input_authorized=False)))


if __name__=='__main__':main()
