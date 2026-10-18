#!/usr/bin/env python3
"""Replace explicit existing PPTX parts, copying every other compressed record verbatim."""
import argparse,copy,hashlib,io,json,zipfile
from pathlib import Path

def record_hashes(path):
 with zipfile.ZipFile(path) as z,path.open('rb') as f:
  infos=sorted(z.infolist(),key=lambda i:i.header_offset);out={}
  for j,i in enumerate(infos):
   end=infos[j+1].header_offset if j+1<len(infos) else z.start_dir
   f.seek(i.header_offset);left=end-i.header_offset;h=hashlib.sha256()
   while left:
    b=f.read(min(left,8*1024*1024))
    if not b:raise ValueError('Truncated ZIP record')
    h.update(b);left-=len(b)
   out[i.filename]=(i.CRC,i.file_size,i.compress_size,i.flag_bits,h.hexdigest())
  return out

def patch(source,output,replacements):
 if output.exists():raise FileExistsError(output)
 if not replacements:raise ValueError('No replacements')
 original=record_hashes(source)
 with zipfile.ZipFile(source) as z,source.open('rb') as raw:
  if len(z.namelist())!=len(set(z.namelist())):raise ValueError('Duplicate ZIP names')
  if not set(replacements)<=set(z.namelist()):raise ValueError('Can only replace existing parts')
  ordered=sorted(z.infolist(),key=lambda i:i.header_offset)
  ends={i.filename:ordered[j+1].header_offset if j+1<len(ordered) else z.start_dir for j,i in enumerate(ordered)}
  try:
   with zipfile.ZipFile(output,'w',allowZip64=True) as out:
    out.comment=z.comment
    for info in z.infolist():
     cloned=copy.copy(info);offset=out.fp.tell()
     if info.filename in replacements:
      mem=io.BytesIO()
      with zipfile.ZipFile(mem,'w',compression=zipfile.ZIP_DEFLATED) as one:one.writestr(copy.copy(info),replacements[info.filename])
      with zipfile.ZipFile(mem) as one:cloned=copy.copy(one.infolist()[0]);end=one.start_dir
      out.fp.write(mem.getvalue()[:end])
     else:
      raw.seek(info.header_offset);left=ends[info.filename]-info.header_offset
      while left:
       b=raw.read(min(left,8*1024*1024))
       if not b:raise ValueError('Truncated ZIP record')
       out.fp.write(b);left-=len(b)
     cloned.header_offset=offset;out.filelist.append(cloned);out.NameToInfo[cloned.filename]=cloned
    out.start_dir=out.fp.tell();out._didModify=True
   after=record_hashes(output)
   unchanged=[n for n in original if n not in replacements]
   if any(original[n]!=after[n] for n in unchanged):raise ValueError('Out-of-scope ZIP record changed')
   with zipfile.ZipFile(output) as z:
    for n,b in replacements.items():
     if z.read(n)!=b:raise ValueError('Replacement verification failed: '+n)
  except Exception:
   output.unlink(missing_ok=True);raise
 return {'ok':True,'replaced_parts':list(replacements),'verbatim_compressed_members':len(unchanged),'bytes':output.stat().st_size}

if __name__=='__main__':
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('source',type=Path);a.add_argument('output',type=Path);a.add_argument('--replace',nargs=2,action='append',required=True,metavar=('PART','FILE'));a.add_argument('--report',type=Path);x=a.parse_args()
 if len({p for p,f in x.replace})!=len(x.replace):a.error('Duplicate replacement part')
 result=patch(x.source,x.output,{p:Path(f).read_bytes() for p,f in x.replace});s=json.dumps(result,ensure_ascii=False,indent=2)
 if x.report:x.report.write_text(s,encoding='utf-8')
 print(s)
