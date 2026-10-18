#!/usr/bin/env python3
"""Audit explicitly encoded Hetu style. Inherited styles and bitmap text need visual review."""
import argparse,json,re,sys,zipfile,xml.etree.ElementTree as ET
from pathlib import Path
from pptx_inventory import NS,slide_parts,select_pages,object_id

def audit(path,slides=None,table_profile=None):
 tokens=json.loads((Path(__file__).resolve().parents[1]/'design-tokens.json').read_text());errors=[];warnings=[];pages=[]
 with zipfile.ZipFile(path) as z:
  pres,parts=slide_parts(z);size=pres.find('p:sldSz',NS);w,h=int(size.get('cx')),int(size.get('cy'))
  for n in select_pages(slides,len(parts)):
   r=ET.fromstring(z.read(parts[n-1]));logos=[];folios=[]
   for el in r.findall('.//p:spTree/*',NS):
    pr=el.find('.//p:cNvPr',NS)
    if pr is None:continue
    name=pr.get('name','');ident=object_id(el);label=f'Page {n} object {ident}';text=''.join(t.text or '' for t in el.findall('.//a:t',NS))
    if name in ['河图统一页脚Logo','hetu-footer-logo']:logos.append(el)
    if name in ['河图统一页码','hetu-footer-folio']:
     folios.append(el)
     if text!=f'{n} / {len(parts)}':errors.append(label+' incorrect actual folio')
    for run in el.findall('.//a:r',NS):
     if not ''.join(t.text or '' for t in run.findall('a:t',NS)).strip():continue
     rp=run.find('a:rPr',NS)
     if rp is None:warnings.append(label+' inherited run properties');continue
     families=[f.get('typeface','') for f in list(rp) if f.tag.rsplit('}',1)[-1] in ['latin','ea']]
     if families and any(f!='Source Han Sans SC Heavy' for f in families):errors.append(label+' non-Heavy font: '+','.join(families))
     if not families:warnings.append(label+' inherited font')
     if rp.get('b') in ['0','false']:errors.append(label+' bold explicitly disabled')
     elif rp.get('b') not in ['1','true']:warnings.append(label+' bold not explicitly set')
    if el.tag.endswith('}pic'):
     sp=el.find('p:spPr',NS)
     if sp is not None:
      ln=sp.find('a:ln',NS)
      if ln is not None and ln.find('a:noFill',NS) is None:errors.append(label+' picture has external stroke')
      ef=sp.find('a:effectLst',NS)
      if ef is not None and len(ef):errors.append(label+' picture has added effects')
    xf=el.find('p:spPr/a:xfrm',NS)
    if xf is not None:
     off=xf.find('a:off',NS)
     if off is not None and int(off.get('x'))>.72*w and int(off.get('y'))<.12*h and re.fullmatch(r'\s*(?:\d+\s*[/／]\s*\d+|第.{1,8}章)\s*',text):errors.append(label+' obsolete top-right metadata')
   if len(logos)!=1:errors.append(f'Page {n} needs one named footer logo, found {len(logos)}')
   if len(folios)!=1:errors.append(f'Page {n} needs one named folio, found {len(folios)}')
   for el,kind in [(e,'logo') for e in logos]+[(e,'folio') for e in folios]:
    xf=el.find('p:spPr/a:xfrm',NS)
    if xf is None:warnings.append(f'Page {n} {kind} inherited geometry');continue
    off=xf.find('a:off',NS);ext=xf.find('a:ext',NS)
    if off is None or ext is None:continue
    x,y=int(off.get('x')),int(off.get('y'));cx,cy=int(ext.get('cx')),int(ext.get('cy'))
    if y<.9*h or y+cy>h:errors.append(f'Page {n} {kind} outside bottom footer band')
    if kind=='logo' and (x>.15*w or cx>.15*w):errors.append(f'Page {n} logo not small left-bottom')
    if kind=='folio' and x<.8*w:errors.append(f'Page {n} folio not bottom-right')
   if table_profile=='green':
    for tbl in r.findall('.//a:tbl',NS):
     for tc in tbl.findall('a:tr/a:tc',NS):
      if not ''.join(t.text or '' for t in tc.findall('.//a:t',NS)):continue
      pr=tc.find('a:tcPr',NS)
      if pr is None or pr.get('anchor')!='ctr':errors.append(f'Page {n} table cell not vertically centered')
      for p in tc.findall('a:txBody/a:p',NS):
       if not ''.join(t.text or '' for t in p.findall('.//a:t',NS)):continue
       pp=p.find('a:pPr',NS)
       if pp is None or pp.get('algn')!='ctr':errors.append(f'Page {n} table cell not horizontally centered')
       for rp in p.findall('a:r/a:rPr',NS):
        if int(rp.get('sz','0'))<1800:errors.append(f'Page {n} table text below 18pt')
      if pr is not None:
       for edge in ['lnL','lnR','lnT','lnB']:
        line=pr.find(f'a:{edge}',NS)
        if line is not None and line.get('w')=='0':continue # shared interior edge suppressed, adjacent cell draws it
        c=pr.find(f'a:{edge}/a:solidFill/a:srgbClr',NS)
        if c is None or c.get('val','').upper()!='A9D9C7':errors.append(f'Page {n} table edge is not pale green')
   pages.append(n)
 return {'ok':not errors,'pages':pages,'errors':sorted(set(errors)),'warnings':sorted(set(warnings)),'limits':'Only explicit object XML is checked; screenshots, inherited style, contrast, visual spacing and playback need manual review.'}

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('pptx',type=Path);p.add_argument('--slides');p.add_argument('--table-profile',choices=['green']);p.add_argument('--output',type=Path);x=p.parse_args();r=audit(x.pptx,x.slides,x.table_profile);s=json.dumps(r,ensure_ascii=False,indent=2)
 if x.output:x.output.write_text(s,encoding='utf-8')
 print(s);sys.exit(0 if r['ok'] else 1)
