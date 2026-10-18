#!/usr/bin/env python3
"""Inventory selected PPTX slides without reading other slides. Standard library only."""
import argparse,hashlib,json,posixpath,re,zipfile
from pathlib import Path
import xml.etree.ElementTree as ET
NS={'p':'http://schemas.openxmlformats.org/presentationml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
def select_pages(spec,total):
 if not spec:return list(range(1,total+1))
 nums=[]
 for token in spec.split(','):
  if '-'in token:
   a,b=map(int,token.split('-',1));nums.extend(range(a,b+1))
  else:nums.append(int(token))
 if len(set(nums))!=len(nums)or any(n<1 or n>total for n in nums):raise ValueError('Invalid or duplicate slide number')
 return nums

def slide_parts(z):
 p=ET.fromstring(z.read('ppt/presentation.xml'));rels={r.get('Id'):r.get('Target')for r in ET.fromstring(z.read('ppt/_rels/presentation.xml.rels'))};out=[]
 for sid in p.findall('p:sldIdLst/p:sldId',NS):
  t=rels[sid.get('{'+NS['r']+'}id')];out.append(t.lstrip('/')if t.startswith('/')else posixpath.normpath(posixpath.join('ppt',t)))
 return p,out

def object_id(el):
 v=el.find('.//p:cNvPr',NS);return v.get('id')if v is not None else None

def inventory(path,pages=None):
 with zipfile.ZipFile(path)as z:
  p,parts=slide_parts(z);result={'slide_count':len(parts),'slide_size_emu':dict(p.find('p:sldSz',NS).attrib),'pages':[]}
  for page in select_pages(pages,len(parts)):
   part=parts[page-1];raw=z.read(part);r=ET.fromstring(raw);objs=[]
   for el in r.find('p:cSld/p:spTree',NS):
    ident=object_id(el)
    if ident is None:continue
    pr=el.find('.//p:cNvPr',NS);xf=el.find('p:spPr/a:xfrm',NS)
    if xf is None:xf=el.find('p:xfrm',NS)
    text=''.join(t.text or ''for t in el.findall('.//a:t',NS));cells=[ ''.join(t.text or ''for t in c.findall('.//a:t',NS))for c in el.findall('.//a:tc',NS)]
    objs.append({'id':ident,'name':pr.get('name',''),'type':el.tag.rsplit('}',1)[-1],'text':text,'cells':cells,'geometry':ET.tostring(xf,encoding='unicode')if xf is not None else None,'picture_embeds':[b.get('{'+NS['r']+'}embed')for b in el.findall('.//a:blip',NS)],'xml_sha256':hashlib.sha256(ET.tostring(el)).hexdigest()})
   result['pages'].append({'page':page,'part':part,'slide_xml_sha256':hashlib.sha256(raw).hexdigest(),'objects':objs,'native_tables':len(r.findall('.//a:tbl',NS)),'video_objects':len(r.findall('.//a:videoFile',NS))})
  return result
if __name__=='__main__':
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('pptx',type=Path);a.add_argument('--slides');a.add_argument('--output',type=Path);x=a.parse_args();data=json.dumps(inventory(x.pptx,x.slides),ensure_ascii=False,indent=2)
 if x.output:x.output.write_text(data,encoding='utf-8')
 else:print(data)
