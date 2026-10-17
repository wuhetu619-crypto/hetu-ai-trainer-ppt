#!/usr/bin/env python3
"""Inspect real PPTX structure; this does not assert visual correctness."""
from pathlib import Path
import argparse
import hashlib
import json
import posixpath
import re
import sys
import urllib.parse
import zipfile
import xml.etree.ElementTree as ET

NS = {'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
      'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
REL = '{http://schemas.openxmlformats.org/package/2006/relationships}'


def compact(s):
    return re.sub(r'\s+', '', s)


def audit(path, expected=None, profile_page=None):
    errors, warnings, details = [], [], []
    with zipfile.ZipFile(path) as z:
        bad = z.testzip()
        if bad:
            errors.append('Corrupt ZIP entry: ' + bad)
        names = set(z.namelist())
        # Check every internal relationship, not just visible slides.
        for name in names:
            if not name.endswith('.rels'):
                continue
            base = '' if name == '_rels/.rels' else posixpath.dirname(posixpath.dirname(name))
            for relationship in ET.fromstring(z.read(name)):
                if relationship.get('TargetMode') == 'External':
                    continue
                target = urllib.parse.unquote(relationship.get('Target', '').split('#')[0])
                resolved = target.lstrip('/') if target.startswith('/') else posixpath.normpath(posixpath.join(base, target))
                if target and resolved not in names:
                    errors.append(f'Missing relationship target: {name} -> {resolved}')
        pres = ET.fromstring(z.read('ppt/presentation.xml'))
        size = pres.find('p:sldSz', NS)
        if size is None or abs(int(size.get('cx')) / int(size.get('cy')) - 16 / 9) > .005:
            errors.append('Canvas is not 16:9')
        rels = {r.get('Id'): r.get('Target') for r in ET.fromstring(z.read('ppt/_rels/presentation.xml.rels'))}
        slide_ids = pres.findall('p:sldIdLst/p:sldId', NS)
        if expected is not None and len(slide_ids) != expected:
            errors.append(f'Expected {expected} slides, found {len(slide_ids)}')
        for index, sid in enumerate(slide_ids, 1):
            target = rels[sid.get('{'+NS['r']+'}id')]
            name = target.lstrip('/') if target.startswith('/') else posixpath.normpath(posixpath.join('ppt', target))
            root = ET.fromstring(z.read(name))
            texts = [n.text or '' for n in root.findall('.//a:t', NS)]
            native = len(root.findall('.//p:sp', NS))
            charts = len(root.findall('.//p:graphicFrame', NS))
            text = '\n'.join(texts)
            if not compact(text) and not charts:
                warnings.append(f'Slide {index}: no native text/table/chart; check image-only flattening')
            details.append({'page': index, 'native_shapes': native, 'graphic_frames': charts,
                            'native_text_characters': len(text), 'first_text': text[:55]})
            if profile_page == index:
                asset_root = Path(__file__).resolve().parents[1]
                profile = json.loads((asset_root/'assets/brand/instructor.json').read_text(encoding='utf-8'))
                for phrase in [profile['name']] + profile['credentials_original']:
                    if compact(phrase) not in compact(text):
                        errors.append(f'Profile page {index}: approved text missing: {phrase}')
                slide_rels = posixpath.join(posixpath.dirname(name), '_rels', posixpath.basename(name) + '.rels')
                hashes = set()
                if slide_rels in names:
                    for rel in ET.fromstring(z.read(slide_rels)):
                        if rel.get('Type', '').endswith('/image'):
                            dest = urllib.parse.unquote(rel.get('Target'))
                            image_name = dest.lstrip('/') if dest.startswith('/') else posixpath.normpath(posixpath.join(posixpath.dirname(name), dest))
                            hashes.add(hashlib.sha256(z.read(image_name)).hexdigest())
                if profile['photo_sha256'] not in hashes:
                    warnings.append(f'Profile page {index}: original photo bytes not directly found; check image identity/crop/compression visually')
        if profile_page and not 1 <= profile_page <= len(slide_ids):
            errors.append('Requested profile page does not exist')
    return {'ok': not errors, 'slides': len(details), 'errors': errors, 'warnings': warnings,
            'pages': details, 'visual_review_required': True}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pptx', type=Path)
    parser.add_argument('--expected-slides', type=int)
    parser.add_argument('--profile-page', type=int)
    args = parser.parse_args()
    try:
        result = audit(args.pptx, args.expected_slides, args.profile_page)
    except Exception as exc:
        result = {'ok': False, 'errors': [str(exc)], 'visual_review_required': True}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result['ok'] else 1)
