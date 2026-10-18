#!/usr/bin/env python3
"""Check exact original text/cell preservation and, for local edits, unchanged objects/parts."""
import argparse,hashlib,json,posixpath,sys,urllib.parse,zipfile,xml.etree.ElementTree as ET
from pathlib import Path
from pptx_inventory import inventory,select_pages,NS,object_id
from patch_pptx_parts import record_hashes

def pairs(values):
 return {tuple(v.split(':',1)) for v in values}

def media_by_object(path,parts):
 result={};cache={}
 with zipfile.ZipFile(path) as z:
  names=set(z.namelist())
  for part in parts:
   relpart=posixpath.join(posixpath.dirname(part),'_rels',posixpath.basename(part)+'.rels');rels={}
   if relpart in names:
    for rel in ET.fromstring(z.read(relpart)):
     typ=rel.get('Type','').rsplit('/',1)[-1]
     if typ not in ['image','audio','video','media']:continue
     target=urllib.parse.unquote(rel.get('Target',''))
     if rel.get('TargetMode')=='External':signature=('external',target)
     else:
      dest=target.lstrip('/') if target.startswith('/') else posixpath.normpath(posixpath.join(posixpath.dirname(part),target))
      if dest not in cache:cache[dest]=hashlib.sha256(z.read(dest)).hexdigest()
      signature=('internal',cache[dest])
     rels[rel.get('Id')]=signature
   root=ET.fromstring(z.read(part));out={}
   for el in root.find('p:cSld/p:spTree',NS):
    ident=object_id(el)
    if ident is None:continue
    refs=[]
    for node in el.iter():
     for k,v in node.attrib.items():
      if k.startswith('{'+NS['r']+'}') and v in rels:refs.append(rels[v])
    out[ident]=sorted(refs)
   result[part]=out
 return result

def compare(source,revised,slides=None,allowed=(),deleted=(),mapping=None):
 a=inventory(source,slides);b=inventory(revised,None if mapping else slides);errors=[]
 local=slides is not None and mapping is None
 if mapping is None and a['slide_count']!=b['slide_count']:errors.append('Slide count changed')
 m={str(p['page']):p['page'] for p in a['pages']}
 if mapping is not None:
  m={str(k):int(v) for k,v in mapping.items()}
  if set(m)!={str(p['page']) for p in a['pages']}:errors.append('Mapping does not cover every original page')
  if len(set(m.values()))!=len(m):errors.append('Original pages must map to distinct preserved pages')
 bp={p['page']:p for p in b['pages']};targetparts=set();checked=0
 am=media_by_object(source,[p['part'] for p in a['pages']])
 bm=media_by_object(revised,[p['part'] for p in b['pages']])
 for page in a['pages']:
  n=page['page'];q=bp.get(m.get(str(n)))
  if q is None:errors.append(f'Missing preserved page {n}');continue
  targetparts.add(page['part']);old={o['id']:o for o in page['objects']};new={o['id']:o for o in q['objects']}
  for ident,o in old.items():
   key=(str(n),ident)
   if ident not in new:
    if key not in deleted:errors.append(f'Page {n} object {ident} removed')
    continue
   v=new[ident];checked+=1
   if o['text']!=v['text']:errors.append(f'Page {n} object {ident} text changed')
   if o['cells']!=v['cells']:errors.append(f'Page {n} object {ident} table cell text changed')
   if am[page['part']].get(ident)!=bm[q['part']].get(ident):errors.append(f'Page {n} object {ident} image/audio/video bytes or relationship changed')
   if local and key not in allowed and o['xml_sha256']!=v['xml_sha256']:errors.append(f'Page {n} object {ident} outside allowed scope changed')
  if local and set(new)-set(old):errors.append(f'Page {n} unexpected new objects: {sorted(set(new)-set(old))}')
 unchanged=None
 if local:
  aa=record_hashes(source);bb=record_hashes(revised)
  if aa.keys()!=bb.keys():errors.append('ZIP member set changed')
  outside=set(aa)-targetparts;unchanged=0
  for name in sorted(outside):
   if aa[name]!=bb.get(name):errors.append('Out-of-scope compressed record changed: '+name)
   else:unchanged+=1
 return {'ok':not errors,'mode':'local' if local else 'content-preservation','original_slides':a['slide_count'],'revised_slides':b['slide_count'],'checked_original_objects':checked,'unchanged_compressed_members':unchanged,'errors':errors,'limits':['Text inside bitmaps, video playback and visual readability require rendering/manual review.','Expansion mapping preserves original objects on mapped pages; splitting originals across new pages requires a dedicated fragment mapping.']}

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('revised',type=Path);p.add_argument('--slides');p.add_argument('--allow-objects',nargs='+',default=[]);p.add_argument('--allow-delete',nargs='+',default=[]);p.add_argument('--mapping',type=Path);p.add_argument('--output',type=Path);x=p.parse_args()
 r=compare(x.source,x.revised,x.slides,pairs(x.allow_objects),pairs(x.allow_delete),json.loads(x.mapping.read_text()) if x.mapping else None);s=json.dumps(r,ensure_ascii=False,indent=2)
 if x.output:x.output.write_text(s,encoding='utf-8')
 print(s);sys.exit(0 if r['ok'] else 1)
