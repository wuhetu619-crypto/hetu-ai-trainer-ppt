#!/usr/bin/env python3
"""Exercise preservation, ZIP-local edits and style failure detection on the native reference."""
import copy,json,tempfile,zipfile,xml.etree.ElementTree as ET
from pathlib import Path
from pptx_inventory import NS,inventory,object_id
from patch_pptx_parts import patch
from compare_decks import compare
from audit_style import audit
from extract_reference_pages import extract

def run():
 root=Path(__file__).resolve().parents[1];source=root/'assets/reference.pptx';checks=[]
 def check(name,condition):
  if not condition:raise AssertionError(name)
  checks.append(name)
 def save_xml(out,part,r):return patch(source,out,{part:ET.tostring(r,encoding='utf-8',xml_declaration=True)})
 check('all native reference pages obey explicit brand rules',audit(source)['ok'])
 check('latest green tables pass centered large-text profile',audit(source,'21,22','green')['ok'])
 inv=inventory(source,'21,22');p=inv['pages'][0];part=p['part'];tid=next(o['id'] for o in p['objects'] if o['cells']);allowed={('21',tid)}
 with zipfile.ZipFile(source) as z:original=ET.fromstring(z.read(part))
 def table(r):return next(e for e in r.find('p:cSld/p:spTree',NS) if object_id(e)==tid)
 with tempfile.TemporaryDirectory(prefix='hetu-v2-regression-') as temp:
  d=Path(temp);r=copy.deepcopy(original)
  for rp in table(r).findall('.//a:rPr',NS):rp.set('sz','1900')
  save_xml(d/'valid.pptx',part,r)
  proof=compare(source,d/'valid.pptx','21,22',allowed)
  check('one-table format change preserves text and all out-of-scope compressed records',proof['ok'] and proof['unchanged_compressed_members']>0)
  r=copy.deepcopy(original);t=table(r).find('.//a:t',NS);t.text=(t.text or '')[:-1];save_xml(d/'text-loss.pptx',part,r)
  check('allowed format object still detects one deleted character',not compare(source,d/'text-loss.pptx','21,22',allowed)['ok'])
  r=copy.deepcopy(original);other=next(e for e in r.find('p:cSld/p:spTree',NS) if object_id(e) and object_id(e)!=tid and e.find('.//a:t',NS) is not None);t=other.find('.//a:rPr',NS);t.set('sz','900');save_xml(d/'scope.pptx',part,r)
  check('unchanged text does not excuse out-of-scope format change',not compare(source,d/'scope.pptx','21,22',allowed)['ok'])
  r=copy.deepcopy(original);font=table(r).find('.//a:rPr/a:latin',NS);font.set('typeface','Source Han Sans SC Regular');save_xml(d/'font.pptx',part,r)
  check('Regular regression is detected',not audit(d/'font.pptx','21')['ok'])
  r=copy.deepcopy(original);table(r).find('.//a:rPr',NS).set('b','0');save_xml(d/'bold.pptx',part,r)
  check('explicit non-bold text is detected',not audit(d/'bold.pptx','21')['ok'])
  r=copy.deepcopy(original);sp=r.find('p:cSld/p:spTree',NS);folio=next(e for e in sp if (e.find('.//p:cNvPr',NS) is not None and e.find('.//p:cNvPr',NS).get('name') in ['河图统一页码','hetu-footer-folio']));sp.append(copy.deepcopy(folio));save_xml(d/'folio.pptx',part,r)
  check('duplicate folio is detected',not audit(d/'folio.pptx','21')['ok'])
  r=copy.deepcopy(original);pic=r.find('.//p:pic/p:spPr',NS);ln=ET.SubElement(pic,'{'+NS['a']+'}ln',w='12700');sf=ET.SubElement(ln,'{'+NS['a']+'}solidFill');ET.SubElement(sf,'{'+NS['a']+'}srgbClr',val='123B5D');save_xml(d/'picture-frame.pptx',part,r)
  check('new picture frame is detected',not audit(d/'picture-frame.pptx','21')['ok'])
  result=extract(source,d/'two.pptx','21,22',True,True)
  check('selected reference extraction preserves native cells',result['output_slides']==2 and inventory(d/'two.pptx')['pages'][0]['objects'][0]['id']==inventory(source,'21')['pages'][0]['objects'][0]['id'])
  two=inventory(d/'two.pptx');expected=[o['cells'] for p in inv['pages'] for o in p['objects'] if o['cells']];actual=[o['cells'] for p in two['pages'] for o in p['objects'] if o['cells']]
  check('extracted tables preserve every cell',expected==actual)
  check('self comparison preserves every original object',compare(source,source)['ok'])
 return {'ok':True,'passed':len(checks),'checks':checks,'scope':'Deterministic native-PPT and failure-injection checks; not a full agent behavior or slideshow playback test.'}

if __name__=='__main__':print(json.dumps(run(),ensure_ascii=False,indent=2))
