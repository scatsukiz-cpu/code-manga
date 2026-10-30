import os,sys,base64,requests,time
H={"Authorization":"Bearer "+os.environ["OPENAI_API_KEY"]}
def gen(out,size,prompt,refs=()):
    for attempt in range(3):
        try:
            if refs:
                files=[("image[]",(os.path.basename(r),open(r,"rb"),"image/png")) for r in refs]
                r=requests.post("https://api.openai.com/v1/images/edits",headers=H,files=files,
                    data={"model":"gpt-image-2","prompt":prompt,"size":size,"quality":"high","n":"1"},timeout=600)
            else:
                r=requests.post("https://api.openai.com/v1/images/generations",headers=H,
                    json={"model":"gpt-image-2","prompt":prompt,"size":size,"quality":"high","n":1},timeout=600)
        except Exception as e:
            err=str(e); time.sleep(5); continue
        if r.status_code==200:
            open(out,"wb").write(base64.b64decode(r.json()["data"][0]["b64_json"])); return "ok"
        err=r.text[:300]
        if "moderation" in err or "safety" in err: return "BLOCKED "+err
        time.sleep(10*(attempt+1))
    return "ERR "+err
if __name__=="__main__":
    print(gen(sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4:]))
