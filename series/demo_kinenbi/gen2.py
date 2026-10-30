# usage: gen2.py out.png size prompt [ref1.png ref2.png ...]
import os,sys,json,base64,requests
out,size,prompt=sys.argv[1],sys.argv[2],sys.argv[3]; refs=sys.argv[4:]
H={"Authorization":"Bearer "+os.environ["OPENAI_API_KEY"]}
if refs:
    files=[("image[]",(os.path.basename(r),open(r,"rb"),"image/png")) for r in refs]
    r=requests.post("https://api.openai.com/v1/images/edits",headers=H,files=files,
        data={"model":"gpt-image-2","prompt":prompt,"size":size,"quality":"high","n":"1"},timeout=600)
else:
    r=requests.post("https://api.openai.com/v1/images/generations",headers=H,
        json={"model":"gpt-image-2","prompt":prompt,"size":size,"quality":"high","n":1},timeout=600)
if r.status_code!=200: print("ERR",out,r.status_code,r.text[:500]); sys.exit(1)
open(out,"wb").write(base64.b64decode(r.json()["data"][0]["b64_json"])); print("ok",out)
