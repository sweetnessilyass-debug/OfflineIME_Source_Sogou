"""Fetch the exact legacy ARM64 offline resource referenced by the supplied APK.

Uses the APK's shipped download configuration, not phone identifiers or accounts.
The response and proprietary archive stay under ignored audit/; only this helper
and the fixed integrity manifest are tracked.
"""
from pathlib import Path
import hashlib,json,re,time,urllib.request

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'audit/offline-voice'; OUT.mkdir(parents=True,exist_ok=True)
SOURCE=ROOT/'audit/jadx/sources/com/sogou/base/filedownload/c.java'
manifest=json.loads((ROOT/'offline-voice/resource-manifest.json').read_text('utf-8'))
match=re.search(r'getResHub\$default\(resHubCenter, "([^"]+)", "([^"]+)"',SOURCE.read_text('utf-8'))
assert match,'Supplied APK download configuration was not found'
app,key=match.groups()
timestamp=int(time.time())
request={'systemID':'10010','appID':app,'timestamp':timestamp,
 'sign':hashlib.md5(f'10010${app}${timestamp}$rdelivery{key}'.encode()).hexdigest(),
 'target':1,'taskIDs':[manifest['task']],'guid':'','isDebugPackage':False}
req=urllib.request.Request('https://rdelivery.qq.com/v1/config/get',
 data=json.dumps(request).encode(),headers={'Content-Type':'application/json'})
with urllib.request.urlopen(req,timeout=30) as response:
    data=response.read()
decoded=json.loads(data)
assert decoded['code']==0
value=decoded['taskIDConfig'][str(manifest['task'])]
assert value['key']==manifest['resource']
config=json.loads(json.loads(value['value'])['config_value'])
assert config['id']==manifest['resource'] and int(config['task_id'])==manifest['task']
assert config['downloadUrl'].startswith('https://sogouinput-honor-1258344701.shiply-cdn.qq.com/')
target=OUT/'offline_zip_64_1.zip'
if not target.exists() or hashlib.sha256(target.read_bytes()).hexdigest()!=manifest['zip_sha256']:
    part=OUT/'offline_zip_64_1.zip.partial'
    with urllib.request.urlopen(config['downloadUrl'],timeout=45) as response,part.open('wb') as f:
        while chunk:=response.read(1024*1024): f.write(chunk)
    assert part.stat().st_size==int(config['size'])
    assert hashlib.md5(part.read_bytes()).hexdigest()==config['md5']
    assert hashlib.sha256(part.read_bytes()).hexdigest()==manifest['zip_sha256']
    part.replace(target)
(OUT/'legacy-resource-response.json').write_bytes(data)
(OUT/'legacy-resource-config.json').write_text(json.dumps(config,ensure_ascii=False,indent=2),'utf-8')
print(f'Pinned offline resource verified: {target.name}, {target.stat().st_size} bytes')
