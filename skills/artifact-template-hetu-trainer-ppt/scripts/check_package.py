#!/usr/bin/env python3
"""Check a relocated Hetu skill package using only Python's standard library."""
from pathlib import Path
import hashlib
import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET


def check(root):
    errors = []
    manifest = json.loads((root / 'assets/manifest.json').read_text(encoding='utf-8'))
    for item in manifest['files']:
        relative = Path(item['path'])
        if relative.is_absolute() or '..' in relative.parts:
            errors.append('Nonportable resource: ' + str(relative))
            continue
        p = root / relative
        if not p.is_file():
            errors.append('Missing: ' + str(relative))
        elif hashlib.sha256(p.read_bytes()).hexdigest() != item['sha256']:
            errors.append('Changed: ' + str(relative))
        elif p.suffix == '.pptx':
            try:
                with zipfile.ZipFile(p) as z:
                    if z.testzip():
                        errors.append('Bad ZIP entry: ' + str(relative))
                    ET.fromstring(z.read('ppt/presentation.xml'))
            except Exception as exc:
                errors.append(f'Invalid PPTX {relative}: {exc}')
    for relative in ['SKILL.md', 'agents/openai.yaml', 'artifact-template.json',
                     'references/approved-assets.md', 'references/teaching-flow.md',
                     'references/input-and-course-design.md', '使用说明.md']:
        if not (root / relative).is_file():
            errors.append('Missing entrypoint/reference: ' + relative)
    template = json.loads((root / 'artifact-template.json').read_text(encoding='utf-8'))
    for key in ['reference', 'preview']:
        relative = Path(template[key])
        if relative.is_absolute() or '..' in relative.parts or not (root / relative).is_file():
            errors.append('Invalid template resource: ' + str(relative))
    profile = json.loads((root / 'assets/brand/instructor.json').read_text(encoding='utf-8'))
    if hashlib.sha256((root / profile['photo']).read_bytes()).hexdigest() != profile['photo_sha256']:
        errors.append('Instructor photo no longer matches approved original')
    version = (root / 'VERSION').read_text().strip()
    tokens = json.loads((root / 'design-tokens.json').read_text())
    if manifest.get('version') != version or tokens.get('version') != version:
        errors.append('Version differs between VERSION, manifest and tokens')
    if f'version: "{version}"' not in (root / 'SKILL.md').read_text():
        errors.append('Entrypoint version differs from VERSION')
    for name in ['pptx_inventory.py','extract_reference_pages.py','patch_pptx_parts.py',
                 'compare_decks.py','audit_style.py','run_regressions.py']:
        if not (root/'scripts'/name).is_file():
            errors.append('Missing executable helper: '+name)
    for md in root.rglob('*.md'):
        for dest in re.findall(r'\]\(([^)]+)\)', md.read_text(encoding='utf-8')):
            if '://' in dest or dest.startswith('#'):
                continue
            target = (md.parent / dest.split('#')[0]).resolve()
            if not target.exists():
                errors.append(f'Broken relative link in {md.relative_to(root)}: {dest}')
    return {'ok': not errors, 'checked_resources': len(manifest['files']), 'errors': errors}


if __name__ == '__main__':
    try:
        result = check(Path(__file__).resolve().parents[1])
    except Exception as exc:
        result = {'ok': False, 'errors': [str(exc)]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result['ok'] else 1)
