#!/usr/bin/env python3
"""Extract only requested slides and required assets; no image re-encoding or slide rasterizing."""
import argparse,copy,posixpath,zipfile,xml.etree.ElementTree as ET
from pathlib import Path
from pptx_inventory import NS,slide_parts,select_pages
PK='http://schemas.openxmlformats.org/package/2006/relationships';R=NS['r']
for prefix,uri in NS.items():ET.register_namespace(prefix,uri)
def xml(x):
 if x.tag.endswith('}Relationships') or x.tag.endswith('}Types'):ET.register_namespace('',x.tag.split('}')[0][1:])
 return ET.tostring(x,encoding='utf-8',xml_declaration=True)
def extract(source,output,pages,renumber=False,omit_notes=False):
 if output.exists():raise FileExistsError(output)
 with zipfile.ZipFile(source)as z:
  pres,sp=slide_parts(z);selected=select_pages(pages,len(sp));ids=pres.find('p:sldIdLst',NS);keep=[ids[n-1]for n in selected];keptids={s.get('{'+R+'}id')for s in keep}
  for s in list(ids):ids.remove(s)
  for s in keep:ids.append(s)
  for s in list(pres):
   if s.tag.rsplit('}',1)[-1]not in ['sldMasterIdLst','sldIdLst','sldSz','notesSz','defaultTextStyle']:pres.remove(s)
  parts={'ppt/presentation.xml':xml(pres)};todo=[];names=set(z.namelist())
  def add(p):
   if p not in parts:parts[p]=z.read(p);todo.append(p)
  rel=ET.fromstring(z.read('ppt/_rels/presentation.xml.rels'))
  for e in list(rel):
   typ=e.get('Type','')
   if typ.endswith('/slide')and e.get('Id')not in keptids:rel.remove(e);continue
   if not any(typ.endswith('/'+s)for s in ['slide','slideMaster','theme']):rel.remove(e);continue
   t=e.get('Target');add(t.lstrip('/')if t.startswith('/')else posixpath.normpath(posixpath.join('ppt',t)))
  parts['ppt/_rels/presentation.xml.rels']=xml(rel)
  while todo:
   p=todo.pop();rp=posixpath.join(posixpath.dirname(p),'_rels',posixpath.basename(p)+'.rels')
   if rp not in names:continue
   rr=ET.fromstring(z.read(rp))
   for e in list(rr):
    if omit_notes and e.get('Type','').endswith('/notesSlide'):rr.remove(e);continue
    if e.get('TargetMode')=='External':continue
    t=e.get('Target');add(t.lstrip('/')if t.startswith('/')else posixpath.normpath(posixpath.join(posixpath.dirname(p),t)))
   parts[rp]=xml(rr)
  if renumber:
   for i,n in enumerate(selected,1):
    p=sp[n-1];root=ET.fromstring(parts[p])
    for sh in root.findall('.//p:sp',NS):
     pr=sh.find('p:nvSpPr/p:cNvPr',NS)
     if pr is not None and pr.get('name')in ['河图统一页码','hetu-footer-folio']:
      ts=sh.findall('.//a:t',NS)
      if len(ts)!=1:raise ValueError('Ambiguous footer; update explicitly')
      ts[0].text=f'{i} / {len(selected)}'
    parts[p]=xml(root)
  ct=ET.fromstring(z.read('[Content_Types].xml'))
  for e in list(ct):
   if e.tag.endswith('}Override')and e.get('PartName','').lstrip('/')not in parts:ct.remove(e)
  parts['[Content_Types].xml']=xml(ct);rr=ET.Element('{'+PK+'}Relationships');ET.SubElement(rr,'{'+PK+'}Relationship',Id='rId1',Type=R+'/officeDocument',Target='ppt/presentation.xml');parts['_rels/.rels']=xml(rr)
  output.parent.mkdir(parents=True,exist_ok=True)
  with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED)as out:
   for n,b in parts.items():out.writestr(n,b)
  return {'selected_pages':selected,'output_slides':len(selected),'bytes':output.stat().st_size}
if __name__=='__main__':
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('source',type=Path);a.add_argument('output',type=Path);a.add_argument('--pages',required=True);a.add_argument('--renumber',action='store_true');a.add_argument('--omit-notes',action='store_true');x=a.parse_args();print(extract(x.source,x.output,x.pages,x.renumber,x.omit_notes))
