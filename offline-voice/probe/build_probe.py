from pathlib import Path
import re,subprocess,sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent.parent
BUILD=HERE/'build'; BUILD.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT))
from build_support import toolchain
SDK,BIN,BT,ANDROID,APKTOOL=toolchain()
source=(ROOT/'audit/jadx/sources/com/sogou/speech/butterfly/BFASRJNIInterface.java').read_text('utf-8')
declarations=re.findall(r'    private static native [^;]+;',source)
assert len(declarations)==25
generated=BUILD/'BFASRJNIInterface.java'
generated.write_text('package com.sogou.speech.butterfly;\nimport java.io.FileDescriptor;\npublic final class BFASRJNIInterface {\n'+'\n'.join(declarations)+'''\n
    public static long probeInit(String path) { return bfjDecoderInitByPath(path, false); }
    public static void probeDestroy(long handle) { bfjDecoderDestroy(handle); }
}\n''',encoding='utf-8')
classes=BUILD/'classes'; classes.mkdir(exist_ok=True)
dex=BUILD/'dex'; dex.mkdir(exist_ok=True)
subprocess.run([str(BIN['javac']),'-encoding','UTF-8','-source','8','-target','8','-d',str(classes),str(generated),str(HERE/'NativeProbe.java')],check=True)
subprocess.run([str(BIN['java']),'-cp',str(BT/'lib/d8.jar'),'com.android.tools.r8.D8','--min-api','21','--lib',str(ANDROID),'--output',str(dex),*[str(p) for p in classes.rglob('*.class')]],check=True)
print(dex/'classes.dex')
