"""Version-pinned, fail-closed local patches for the user-supplied APK.

No upstream APK, dictionaries, decompiled code or signing keys are part of this script.
The original decoded audit directory is treated as read-only.
"""
from pathlib import Path
import hashlib, json, re, shutil, sys, xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from build_support import ORIGINAL, KEY
SRC = ROOT / 'audit/decoded'
WORK = ROOT / 'offline-voice/work'
LOG = []
EXPECTED = '3eb2612040fd7daefb7e92b9de5c1a715b03f272b644e0664948742df1c7a416'
assert hashlib.sha256(ORIGINAL.read_bytes()).hexdigest() == EXPECTED
WORK.mkdir(parents=True, exist_ok=True)
if not (WORK / '.copied').exists():
    shutil.copytree(SRC, WORK, dirs_exist_ok=True)
    (WORK / '.copied').write_text(EXPECTED)

def smali(cls):
    files = list(SRC.glob('smali*/' + cls + '.smali'))
    assert len(files) == 1, (cls, files)
    return files[0].relative_to(SRC)

texts = {}
def get(cls):
    rel = smali(cls)
    if rel not in texts:
        texts[rel] = (SRC / rel).read_text(encoding='utf-8')
    return rel, texts[rel]

def replace(cls, signature, body, reason):
    rel, text = get(cls)
    pat = r'(?m)^\.method ([^\n]* (?<!\S)' + re.escape(signature) + r')\n[\s\S]*?^\.end method'
    found = list(re.finditer(pat, text))
    assert len(found) == 1, (cls, signature, len(found))
    m = found[0]
    texts[rel] = text[:m.start()] + '.method ' + m[1] + '\n' + body.strip('\n') + '\n.end method' + text[m.end():]
    LOG.append({'class':cls,'method':signature,'reason':reason})

def void(cls, sig, why):
    replace(cls, sig, '    .locals 0\n    return-void', why)

def false(cls, sig, why):
    replace(cls, sig, '    .locals 1\n    const/4 v0, 0x0\n    return v0', why)

def inject_returns(cls, sig, code, why):
    rel, text = get(cls)
    pat = r'(?m)^\.method [^\n]* ' + re.escape(sig) + r'\n[\s\S]*?^\.end method'
    found = list(re.finditer(pat,text)); assert len(found)==1,(cls,sig)
    m=found[0]
    body,n=re.subn(r'(?m)^    return-void$',code+'\n    return-void',m[0])
    assert n>0,(cls,sig)
    texts[rel]=text[:m.start()]+body+text[m.end():]
    LOG.append({'class':cls,'method':sig,'reason':why})

# Keep application loading, input-engine startup and first-install migrations.
# Only these independently identified commercial/telemetry initializers are no-ops.
for cls in [
    'com/sohu/inputmethod/beaconbridge/init/a',
    'com/sogou/inputmethod/dt/d',
    'com/sogou/imskit/feature/lib/game/center/core/init/a',
    'com/sogou/imskit/feature/lib/tangram/init/c',
]:
    void(cls,'run(Landroid/content/Context;)V','Disable identified commercial/telemetry initializer')
# This initializer only stores Context and a false flag. Keep its dependency
# contract; disable collection at its own entry points instead.
get('com/sohu/inputmethod/sogou/bigdata/b')
LOG.append({'class':'com/sohu/inputmethod/sogou/bigdata/b','reason':'Restore context-only initializer required by existing callers'})
for sig in ['u()V','v()V','s(I)V','t(I)V','y(I)V']:
    void('com/sohu/inputmethod/sogou/bigdata/d',sig,'Disable telemetry tasks reached after committing input')
false('com/sogou/hj/task/f','a()Z','Disable downloaded telemetry task execution')

# Fixed offline configuration: retain local input functionality without opening
# the vendor online-consent flow. INTERNET remains absent from the manifest.
replace('com/sogou/bu/basic/data/support/settings/SettingManager','a0()I',
 '    .locals 1\n    const/4 v0, 0x1\n    return v0',
 'Use local functionality mode without first-run online-service dialog')
get('com/sohu/inputmethod/sogou/AppPopWinManager')
for sig in ['bb()Z','m6()Z']:
    false('com/sogou/imskit/feature/keyboard/ai/router/f',sig,'Disable cloud AI service and associated search entry')
void('com/sogou/imskit/feature/keyboard/ai/router/f',
 'm(Ljava/lang/Class;Landroid/os/Bundle;Lcom/sogou/imskit/feature/keyboard/ai/container/AiEntrySource;)V',
 'Do not open removed cloud AI pages')
for cls in ['com/sohu/inputmethod/sogou/launch/i$a','com/sohu/inputmethod/sogou/launch/i$b','com/sohu/inputmethod/sogou/launch/i$c']:
    void(cls,'j()V','Complete startup task without collection, hotfix or game preloading')
for sig in ['initLoggerBeacon()V','initAndStartExceptionMonitor()V']:
    void('com/sohu/inputmethod/sogou/SogouAppApplication',sig,'Disable upload timer/crash SDK startup')
for sig in ['c(Landroid/content/Context;)V','d(Landroid/app/Application;)V','e()V','f(Ljava/lang/Throwable;)V','g(Landroid/content/Context;)V','h(Ljava/lang/String;)V','i(Ljava/lang/String;)V']:
    void('com/sogou/scrashly/e',sig,'Disable diagnostics wrapper and dependent calls after SDK removal')
for sig in ['a()V','f()V','g()V']:
    void('com/sohu/inputmethod/beaconbridge/b',sig,'Disable deferred beacon initialization/upload')
for sig in ['y0(Z)Z','x0(Z)Z','w0(Z)Z']:
    false('com/sogou/core/input/chinese/settings/b',sig,'Disable advertising/emoji advertising recommendation gates; preserve local prediction')
false('com/sogou/core/input/chinese/settings/b','B0()Z','Disable cloud input switch')
inject_returns('com/sogou/imskit/feature/settings/preference/InputSettingFragment',
 'onViewCreated(Landroid/view/View;Landroid/os/Bundle;)V',
 '    invoke-static {p0}, Llocal/sogoulite/OfflinePolicy;->trimInputSettings(Ljava/lang/Object;)V',
 'Hide disabled cloud input and commercial recommendation settings')
void('com/sogou/base/hotfix/d','i()V','Disable patch requests')
void('com/sogou/base/hotfix/d','g(Lcom/tencent/rfix/entry/RFixApplicationLike;Lcom/sogou/base/hotfix/h;)V','Disable RFix SDK initialization while retaining application loader')
replace('com/sogou/base/hotfix/d','f()Ljava/lang/String;','    .locals 1\n    const/4 v0, 0x0\n    return-object v0','No loaded remote patch identifier')
void('com/sogou/bu/netswitch/c','c(ZLcom/sogou/bu/netswitch/i;)V','Disable remote configuration fetch')
void('com/sogou/inputmethod/tipspush/b','c(Landroid/content/Context;Ljava/lang/String;)V','Disable push registration')
replace('com/tencent/upgrade/download/DefaultDownLoader',
 'download(Ljava/lang/String;JLjava/lang/String;Ljava/lang/String;Lcom/tencent/upgrade/callback/DownloadListener;)V',
 '''    .locals 2
    if-eqz p6, :done
    new-instance v0, Ljava/io/IOException;
    const-string v1, "Offline build: updates are disabled"
    invoke-direct {v0, v1}, Ljava/io/IOException;-><init>(Ljava/lang/String;)V
    invoke-interface {p6, v0}, Lcom/tencent/upgrade/callback/DownloadListener;->onFail(Ljava/lang/Exception;)V
    :done
    return-void''','Complete update download with offline failure; never delegate to DownloadManager')
void('com/tencent/upgrade/download/DefaultDownLoader','stop()V','No download exists in offline build')

# Report the actual offline policy to app-level callers, even when the phone is online.
net='com/sogou/lib/common/network/d'
for sig in ['b()Z','d()Z','f(Landroid/content/Context;)Z','g(Landroid/content/Context;)Z','h()Z','i(Landroid/content/Context;)Z','j(Landroid/content/Context;IZ)Z','k()Z','l(Landroid/content/Context;)Z','m(ILandroid/content/Context;)Z','n()Z','o(Landroid/content/Context;)Z','p(Landroid/content/Context;IZ)Z','q(ILandroid/content/Context;)Z']:
    false(net,sig,'App-level network availability is always offline')
replace(net,'a(ILandroid/content/Context;)Landroid/net/NetworkInfo;','    .locals 1\n    const/4 v0, 0x0\n    return-object v0','No usable network')
replace(net,'c()I','    .locals 1\n    const/4 v0, -0x1\n    return v0','No active network type')

# The business quick-portal adapter is separate from local candidates and clipboard.
qp='com/sogou/quickportal/a'
for sig in ['I5()Z','Wu()Z','c0()Z','jo()Z']:
    false(qp,sig,'Hide commercial quick portal')
for sig in ['Ag()V','Cf()V','Do(Lcom/sohu/inputmethod/common/bean/QuickPortalModel;)V','Lq()V','Ol()V','Qu()V','Sb(II)V','To(Z)V','h2()V','k9()V','lu()V','recycle()V','st()V','tq()V','yf()V']:
    void(qp,sig,'Do not initialize/show/update commercial quick portal')

# Filter both toolbar and toolbox after every processing chain, so a later task
# cannot reinsert promotional entries. Only local input tools are allowed.
inject_returns('com/sogou/keyboard/toolskit/pipeline/a',
 'b(Lcom/sogou/keyboard/toolskit/pipeline/e;Landroid/content/Context;Lcom/sogou/keyboard/toolskit/pipeline/SceneType;)V',
 '    invoke-static {p1}, Llocal/sogoulite/OfflinePolicy;->filterTools(Ljava/lang/Object;)V',
 'Filter toolbar/toolbox to local input features')

# Redirect launchers without running the advertising/home flow.
nav='com/sogou/keyboard/toolkit/native_impl/view/ToolkitNavigationBar'
for sig in ['<init>(Landroid/content/Context;Landroid/util/AttributeSet;I)V','i(Lcom/sogou/keyboard/toolkit/data/m;ZZZ)V','setRightExtraEntriesVisible(Z)V','setCrossDeviceRedDotVisible(Z)V']:
    inject_returns(nav,sig,'    invoke-static {p0}, Llocal/sogoulite/OfflinePolicy;->trimNavigation(Landroid/view/View;)V','Hide login, VIP and cross-device cloud controls; retain back and local settings')

for cls in ['com/sohu/inputmethod/sogou/SogouIMELauncher','com/sohu/inputmethod/sogou/SogouIMESettingsLauncher']:
    replace(cls,'onCreate(Landroid/os/Bundle;)V',
    '    .locals 0\n    invoke-super {p0, p1}, Landroid/app/Activity;->onCreate(Landroid/os/Bundle;)V\n    invoke-static {p0}, Llocal/sogoulite/LiteActivity;->open(Landroid/app/Activity;)V\n    return-void',
    'Open offline local settings')

# The original settings wrapper only creates a dynamic settings page. Retain its
# class identity for generated routers while supplying our local settings screen.
cls='com/sohu/inputmethod/sogou/SogouIMESettings'
rel=smali(cls)
texts[rel]='''.class public Lcom/sohu/inputmethod/sogou/SogouIMESettings;
.super Llocal/sogoulite/LiteActivity;
.source "SogouLiteLocalSettings.java"
.method public constructor <init>()V
    .locals 0
    invoke-direct {p0}, Llocal/sogoulite/LiteActivity;-><init>()V
    return-void
.end method
'''
LOG.append({'class':cls,'reason':'Replace dynamic settings wrapper with local settings'})

# Manifest-level network boundary and harmless canceled results for removed pages.
A='{http://schemas.android.com/apk/res/android}'
ET.register_namespace('android',A[1:-1])
tree=ET.parse(SRC/'AndroidManifest.xml'); root=tree.getroot(); app=root.find('application')
keep_permissions={
 'android.permission.RECORD_AUDIO',
 'android.permission.VIBRATE','android.permission.WAKE_LOCK',
 'android.permission.ACCESS_NETWORK_STATE','android.permission.ACCESS_WIFI_STATE',
 'android.permission.READ_EXTERNAL_STORAGE','android.permission.WRITE_EXTERNAL_STORAGE',
 'android.permission.MODIFY_AUDIO_SETTINGS','android.permission.FOREGROUND_SERVICE',
 'com.sohu.inputmethod.sogou.permission.KUIKLY_NOTIFY',
}
removed_permissions=[]
for el in list(root):
    if el.tag.startswith('uses-permission') and el.get(A+'name') not in keep_permissions:
        removed_permissions.append(el.get(A+'name')); root.remove(el)
assert 'android.permission.INTERNET' in removed_permissions
app.set(A+'usesCleartextTraffic','false'); app.set(A+'label','搜狗离线语音')
app.set(A+'allowBackup','false'); app.set(A+'debuggable','false')
# These declarations precede their aliases as required by PackageParser.
app.insert(0,ET.Element('activity',{A+'name':'local.sogoulite.LiteActivity',A+'exported':'false',A+'theme':'@android:style/Theme.Material.Light.NoActionBar',A+'windowSoftInputMode':'adjustResize'}))
app.insert(1,ET.Element('activity',{A+'name':'local.sogoulite.RemovedActivity',A+'exported':'false',A+'theme':'@android:style/Theme.Translucent.NoTitleBar',A+'excludeFromRecents':'true'}))

commerce_prefixes=(
 'com.sogou.theme.', 'com.sogou.home.', 'com.sogou.explorer.',
 'com.sogou.account.', 'com.sogou.passport', 'com.sogou.imskit.feature.account.',
 'com.sogou.imskit.feature.home.', 'com.sogou.imskit.feature.lib.vip.',
 'com.sogou.imskit.feature.lib.game.', 'com.sogou.imskit.feature.lib.tangram.',
 'com.sogou.imskit.feature.skin', 'com.sogou.imskit.feature.font',
 'com.sogou.imskit.feature.settings.feedback.', 'com.sogou.listentalk.',
 'com.sogou.airecord.', 'com.sogou.copytranslate.', 'com.sogou.upgrade.',
 'com.sogou.ipsgame.', 'com.sogou.replugin.', 'com.sogou.teemo.',
 'com.sogou.pay.', 'com.sogou.inputmethod.pay.', 'com.sogou.stick.route.',
 'com.sohu.inputmethod.skinmaker.', 'com.bbk.account.',
 'com.tencent.', 'com.qq.e.', 'com.huawei.', 'com.hihonor.',
 'com.xiaomi.', 'com.heytap.', 'com.vivo.', 'com.sina.', 'com.alipay.',
 'base.sogou.mobile.', 'com.sohu.inputmethod.account.',
 'com.sohu.inputmethod.splashscreen.', 'com.sohu.inputmethod.cooperation.',
 'com.sohu.inputmethod.sogou.cooperation.', 'com.sohu.inputmethod.wallpaper.',
 'com.sohu.inputmethod.commercialnotification.', 'com.sohu.inputmethod.translator.',
 'com.sohu.inputmethod.voiceinput.accessories.', 'com.sohu.inputmethod.flx.',
 'com.sdk.doutu.', 'com.sohu.inputmethod.qrcode.',
)
commerce_terms=('AccountLogin','GameCenter','SkinPreview','ThemePreview','AdVideo',
 'SmartDeeplink','WebViewActivity','Payment','VipActivity','Upgrade','LoginActivity',
 'DataSyncSettings','UserInfoDownloadSettings','UserinfoCapital','LogFeedBack',
 'ChatRoom','AiSearch','SearchActivity','Donation','Welfare','FontShop','TuxWebActivity')
home='com.sohu.inputmethod.sogou.SogouIMEHomeActivity'
aliased=[]; disabled=[]
for el in list(app):
    name=el.get(A+'name','')
    if el.tag=='activity' and (name==home or name.startswith(commerce_prefixes) or any(s in name for s in commerce_terms)):
        target='local.sogoulite.LiteActivity' if name==home else 'local.sogoulite.RemovedActivity'
        alias=ET.Element('activity-alias',{A+'name':name,A+'targetActivity':target,A+'exported':'false',A+'enabled':'true'})
        idx=list(app).index(el); app.remove(el); app.insert(idx,alias)
        aliased.append(name)
    elif el.tag in ('service','receiver','provider'):
        keep_names={
          'androidx.lifecycle.ProcessLifecycleOwnerInitializer','androidx.startup.InitializationProvider',
          'androidx.core.content.FileProvider','androidx.profileinstaller.ProfileInstallReceiver',
          'com.sohu.inputmethod.sogou.SogouIME','com.sogou.bu.ipc.provider.SKeyboardProvider',
          'com.sogou.bu.ipc.provider.SAppProvider','com.sogou.imskit.feature.settings.SogouContentProvider',
          'com.sogou.imskit.feature.settings.status.SogouStatusService',
          'com.sogou.imskit.feature.settings.status.CheckSogouIMStatusReceiver',
          'com.sogou.userguide.SettingGuideService','com.sogou.base.permission.bridge.BridgeReceiver',
          'com.sogou.base.stimer.STimerReceiver',
          'com.sogou.lib.common.notification.NotificationServiceImpl$NotificationReceiver',
          'com.sogou.input.service.RequestBodyService',
        }
        if name not in keep_names and not name.startswith(('com.sogou.remote.','com.qihoo360.replugin.')):
            el.set(A+'enabled','false'); el.set(A+'exported','false'); disabled.append(name)
    if name in ('com.sohu.inputmethod.sogou.SogouIMELauncher','com.sohu.inputmethod.sogou.SogouIMEAliasLauncher','com.sohu.inputmethod.sogou.SogouIME'):
        el.set(A+'label','搜狗离线语音')
ET.indent(tree,space='    '); tree.write(WORK/'AndroidManifest.xml',encoding='utf-8',xml_declaration=True)

# Original offline SDK integration. The manifest still excludes INTERNET.
def prepend(cls, sig, code, why):
    rel, text = get(cls)
    pat=r'(?m)^\.method [^\n]* '+re.escape(sig)+r'\n[\s\S]*?^\.end method'
    found=list(re.finditer(pat,text)); assert len(found)==1,(cls,sig)
    m=found[0]
    body,n=re.subn(r'(?m)^(    \.locals \d+)$',lambda x:x[0]+'\n'+code,m[0],count=1)
    assert n==1,(cls,sig)
    texts[rel]=text[:m.start()]+body+text[m.end():]
    LOG.append({'class':cls,'method':sig,'reason':why})

prepend('com/sohu/inputmethod/sogou/SogouAppApplication','onCreate()V',
 '    invoke-static/range {p0 .. p0}, Llocal/sogoulite/OfflineVoiceAssets;->initialize(Ljava/lang/Object;)V',
 'Prepare checksum-pinned bundled offline voice assets in background')
resource='com/sogou/inputmethod/voiceinput/resource/a0'
replace(resource,'p()Z','    .locals 1\n    invoke-static {}, Llocal/sogoulite/OfflineVoiceAssets;->isReady()Z\n    move-result v0\n    return v0','Report bundled resource readiness')
replace(resource,'h()I','    .locals 1\n    invoke-static {}, Llocal/sogoulite/OfflineVoiceAssets;->version()I\n    move-result v0\n    return v0','Report pinned bundled resource version')
replace(resource,'k()Lcom/sogou/inputmethod/voiceinput/resource/o;','    .locals 1\n    invoke-static {}, Llocal/sogoulite/OfflineVoiceAssets;->descriptor()Ljava/lang/Object;\n    move-result-object v0\n    check-cast v0, Lcom/sogou/inputmethod/voiceinput/resource/o;\n    return-object v0','Use local verified paths instead of downloaded resource metadata')
replace(resource,'s(Z)Lcom/sogou/inputmethod/voiceinput/resource/n;','    .locals 1\n    invoke-static {p1}, Llocal/sogoulite/OfflineVoiceAssets;->load(Z)Ljava/lang/Object;\n    move-result-object v0\n    check-cast v0, Lcom/sogou/inputmethod/voiceinput/resource/n;\n    return-object v0','Load bundled original offline JNI libraries')
replace('com/sogou/bu/basic/data/support/settings/SettingManager','b3()Z','    .locals 1\n    const/4 v0, 0x1\n    return v0','Keep bundled offline recognition enabled')
for sig in ['x()Z','y()Z']:
    false('com/sogou/inputmethod/voice/sdk/sogounew/a',sig,'Use original Java pipeline and Butterfly offline JNI backend')
false('com/sogou/inputmethod/voiceinput/settings/e','v0()Z','Do not disable available bundled offline recognition by remote switch')
prepend('com/sogou/ai/nsrss/engine/SogouAsrEngine$Builder','withAsrConfig(Lcom/sogou/ai/nsrss/modules/conf/AsrConfig;)Lcom/sogou/ai/nsrss/engine/SogouAsrEngine$Builder;',
 '    invoke-static/range {p1 .. p1}, Llocal/sogoulite/OfflineVoiceAssets;->configure(Ljava/lang/Object;)V',
 'Force OFFLINE_ONLY at final builder boundary with actual bundled model paths')
void('com/sogou/ai/nsrss/network/HttpClient','buildConnection(Lokhttp3/OkHttpClient;Ljava/lang/String;Lcom/sogou/ai/nsrss/network/PreConnectListener;)V','Disable online connection prewarming')
for cls in ['VoiceQualityBeaconAudio','VoiceQualityBeaconAudioOcc']:
    void('com/sogou/inputmethod/voiceinput/pingback/'+cls,'recordBeacon()V','Disable voice quality telemetry')
prepend('com/sogou/inputmethod/voice_input/g','r(ILcom/sogou/inputmethod/voice/interfaces/IVoiceInputConfig;ZILcom/sogou/inputmethod/voice/interfaces/view/c;Ljava/lang/String;)I',
 '''    invoke-static {}, Llocal/sogoulite/OfflineVoiceAssets;->isReady()Z
    move-result v0
    if-nez v0, :local_voice_assets_ready
    invoke-static {}, Llocal/sogoulite/OfflineVoiceAssets;->notReady()V
    const/4 v0, -0x3
    return v0
    :local_voice_assets_ready
    invoke-static {}, Llocal/sogoulite/OfflineVoiceAssets;->sessionBegin()V''',
 'Wait for verified resources before opening a microphone session')
prepend('com/sogou/inputmethod/voice_input/g','h()V',
 '    invoke-static {}, Llocal/sogoulite/OfflineVoiceAssets;->sessionStop()V','Record session completion without audio or recognized text')
cls='com/sogou/speech/butterfly/BFASRJNIInterface'
rel,text=get(cls)
for sig in ['initDecoder(Ljava/lang/String;Z)J','initDecoder(Ljava/io/FileDescriptor;JZ)J']:
    pat=r'(?m)^\.method [^\n]* '+re.escape(sig)+r'\n[\s\S]*?^\.end method'
    found=list(re.finditer(pat,text)); assert len(found)==1
    m=found[0]
    def log_return(match):
        reg=match[1]; nxt=reg[0]+str(int(reg[1:])+1)
        return f'    invoke-static/range {{{reg} .. {nxt}}}, Llocal/sogoulite/OfflineVoiceAssets;->nativeInitResult(J)V\n'+match[0]
    body,n=re.subn(r'(?m)^    return-wide ([vp]\d+)$',log_return,m[0]); assert n>0
    text=text[:m.start()]+body+text[m.end():]
texts[rel]=text
LOG.append({'class':cls,'reason':'Record decoder initialization success without exporting native handles'})

bundle=WORK/'assets/offline-voice'; bundle.mkdir(parents=True,exist_ok=True)
archive=ROOT/'audit/offline-voice/offline_zip_64_1.zip'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='8f934758d7e4dbf15bcf31f1335a7cb6d4cb6e39590849019c34d96699450281'
shutil.copy2(archive,bundle/'resources.zip')
shutil.copy2(ROOT/'offline-voice/resource-manifest.json',bundle/'resource-manifest.json')

for rel,text in texts.items():
    target=WORK/rel
    if target.read_text(encoding='utf-8')!=text:
        target.write_text(text,encoding='utf-8')

# native_setup compares MD5(Signature.toCharsString()) before allocating the
# engine handle. Re-signing requires the new public certificate here. Replace
# the literal only: all native instructions and dictionary bytes stay intact.
native=SRC/'lib/arm64-v8a/libsogouime.so'
raw=native.read_bytes()
old=b'449fb4a5bba953fe3e2b5a49277bd642'
cert=(KEY/'signer.der').read_bytes()
new=hashlib.md5(cert.hex().encode('ascii')).hexdigest().encode('ascii')
assert raw.count(old)==1
offset=raw.index(old)
patched=raw[:offset]+new+raw[offset+32:]
assert len(patched)==len(raw)
outnative=WORK/'lib/arm64-v8a/libsogouime.so'
if outnative.read_bytes()!=patched:
    outnative.write_bytes(patched)
LOG.append({'file':'lib/arm64-v8a/libsogouime.so','offset':offset,'length':32,'old':old.decode(),'new':new.decode(),'reason':'Trust the actual local signing certificate; native executable code unchanged'})
# Remove stale DEX optimization metadata; byte offsets changed during assembly.
for name in ['assets/dexopt/baseline.prof','assets/dexopt/baseline.profm']:
    (WORK/name).unlink(missing_ok=True)
(WORK/'patch-log.json').write_text(json.dumps({'source_sha256':EXPECTED,'patches':LOG,'removed_permissions':removed_permissions,'redirected_activities':aliased,'disabled_components':disabled},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'methods':len(LOG),'removed_permissions':len(removed_permissions),'redirected_activities':len(aliased),'disabled_components':len(disabled)},ensure_ascii=False))
