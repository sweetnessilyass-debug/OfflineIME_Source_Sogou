from pathlib import Path
import hashlib, io, json, subprocess, sys, zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
sys.path.insert(0,str(ROOT))
from build_support import ORIGINAL, KEY, toolchain, signing_material
SDK, BIN, BT, ANDROID, APKTOOL = toolchain()
OUT=HERE/'build'; OUT.mkdir(exist_ok=True)
LOG=HERE/'logs'; LOG.mkdir(exist_ok=True)
def run(name,args):
    print(name,flush=True)
    with (LOG/(name+'.log')).open('w',encoding='utf-8') as f:
        p=subprocess.run([str(x) for x in args],stdout=f,stderr=subprocess.STDOUT)
    if p.returncode:
        print((LOG/(name+'.log')).read_text(encoding='utf-8',errors='replace')[-9000:])
        raise SystemExit(p.returncode)

password,keystore=signing_material(run,BIN)
run('patch',[sys.executable,HERE/'patch_apk.py'])
classes=OUT/'classes'; classes.mkdir(exist_ok=True)
dex=OUT/'dex'; dex.mkdir(exist_ok=True)
run('javac',[BIN['javac'],'-encoding','UTF-8','-source','8','-target','8','-classpath',ANDROID,'-d',classes,*sorted((HERE/'java').rglob('*.java'))])
run('d8',[BIN['java'],'-cp',BT/'lib/d8.jar','com.android.tools.r8.D8','--release','--min-api','21','--lib',ANDROID,'--output',dex,*sorted(classes.rglob('*.class'))])
run('apktool-build',[BIN['java'],'-Xmx5g','-jar',APKTOOL,'b',HERE/'work','-p',ROOT/'tools/apktool-framework','-o',OUT/'unsigned.apk'])
with zipfile.ZipFile(OUT/'unsigned.apk','a',compression=zipfile.ZIP_DEFLATED) as z:
    assert 'classes8.dex' not in z.namelist()
    z.write(dex/'classes.dex','classes8.dex')
run('zipalign',[BIN['zipalign'],'-f','-p','4',OUT/'unsigned.apk',OUT/'aligned.apk'])
DIST=ROOT/'dist'; DIST.mkdir(exist_ok=True)
apk=DIST/'SogouInput_20.17.0_Lite_OfflineVoice_0.2_arm64.apk'
run('sign',[BIN['java'],'-jar',BT/'lib/apksigner.jar','sign','--ks',keystore,'--ks-key-alias','sogou-lite','--ks-pass','file:'+str(password),'--v1-signing-enabled','true','--v2-signing-enabled','true','--v3-signing-enabled','true','--v4-signing-enabled','false','--out',apk,OUT/'aligned.apk'])
run('verify-signature',[BIN['java'],'-jar',BT/'lib/apksigner.jar','verify','--verbose','--print-certs',apk])
run('verify-alignment',[BIN['zipalign'],'-c','-p','4',apk])
run('badging',[BIN['aapt'],'dump','badging',apk])
run('permissions',[BIN['aapt'],'dump','permissions',apk])
permissions=(LOG/'permissions.log').read_text()
assert "name='android.permission.INTERNET'" not in permissions
assert "name='android.permission.RECORD_AUDIO'" in permissions
with zipfile.ZipFile(ORIGINAL) as src,zipfile.ZipFile(apk) as dst:
    kept=[n for n in src.namelist() if n.startswith(('lib/','assets/raw/','assets/foreign/','assets/keyboard/','assets/theme/')) and not n.endswith('/')]
    kept.remove('lib/arm64-v8a/libsogouime.so')
    mismatch=[n for n in kept if src.read(n)!=dst.read(n)]
    assert not mismatch,mismatch
    original=src.read('lib/arm64-v8a/libsogouime.so')
    native=dst.read('lib/arm64-v8a/libsogouime.so')
    old=b'449fb4a5bba953fe3e2b5a49277bd642'; offset=original.index(old)
    new=hashlib.md5((KEY/'signer.der').read_bytes().hex().encode('ascii')).hexdigest().encode('ascii')
    assert native==original[:offset]+new+original[offset+32:]
    manifest_bytes=(HERE/'resource-manifest.json').read_bytes()
    manifest=json.loads(manifest_bytes)
    assert dst.read('assets/offline-voice/resource-manifest.json')==manifest_bytes
    resource_bytes=dst.read('assets/offline-voice/resources.zip')
    assert hashlib.sha256(resource_bytes).hexdigest()==manifest['zip_sha256']
    with zipfile.ZipFile(io.BytesIO(resource_bytes)) as bundle:
        names=[n for n in bundle.namelist() if not n.endswith('/')]
        assert len(names)==len(set(names)) and set(names)==set(manifest['files'])
        for name,info in manifest['files'].items():
            data=bundle.read(name)
            assert len(data)==info['bytes'] and hashlib.sha256(data).hexdigest()==info['sha256'],name
    evidence={'apk':apk.name,'sha256':hashlib.sha256(apk.read_bytes()).hexdigest(),'bytes':apk.stat().st_size,'preserved_input_files':len(kept),'input_file_mismatches':mismatch,'native_core_changes':{'offset':offset,'length':32,'kind':'local certificate digest data only','executable_code_identical':True},'internet_permission':False,'bundled_offline_voice':True,'signature_verified':True,'runtime_tested':False}
    evidence.update(resource_zip_sha256_verified=manifest['zip_sha256'],resource_files=len(manifest['files']))
(OUT/'build-verification.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(evidence,ensure_ascii=False),flush=True)
