"""Local build configuration. Keep downloaded inputs and signing material private."""
from pathlib import Path
import os
import shutil

ROOT = Path(__file__).resolve().parent
ORIGINAL = ROOT / 'inputs/SogouInput_20.17.0_android_sweb.apk'
EXPECTED = '3eb2612040fd7daefb7e92b9de5c1a715b03f272b644e0664948742df1c7a416'
KEY = ROOT / '.local/signing'


def required_file(path, label):
    path = Path(path)
    if not path.is_file():
        raise SystemExit(f'{label} was not found; see README.md for local prerequisites.')
    return path


def toolchain():
    sdk_value = os.environ.get('ANDROID_SDK_ROOT') or os.environ.get('ANDROID_HOME')
    if not sdk_value and os.environ.get('LOCALAPPDATA'):
        sdk_value = str(Path(os.environ['LOCALAPPDATA']) / 'Android/Sdk')
    if not sdk_value:
        raise SystemExit('Set ANDROID_SDK_ROOT before building.')
    sdk = Path(sdk_value)
    java_home = os.environ.get('JAVA_HOME')
    javac = shutil.which('javac')
    if java_home:
        jdk = Path(java_home) / 'bin'
    elif javac:
        jdk = Path(javac).resolve().parent
    else:
        raise SystemExit('Set JAVA_HOME to a JDK, or put javac on PATH.')
    ext = '.exe' if os.name == 'nt' else ''
    binaries = {name: required_file(jdk / (name + ext), name)
                for name in ('java', 'javac', 'keytool')}
    bt = sdk / 'build-tools' / os.environ.get('ANDROID_BUILD_TOOLS', '36.1.0')
    android = required_file(sdk / 'platforms' / os.environ.get('ANDROID_PLATFORM', 'android-36') / 'android.jar', 'Android platform')
    apktool = required_file(os.environ.get('APKTOOL_JAR', ROOT / 'tools/apktool_3.0.3.jar'), 'apktool')
    for name in ('aapt', 'zipalign'):
        binaries[name] = required_file(bt / (name + ext), name)
    for name in ('d8', 'apksigner'):
        required_file(bt / 'lib' / (name + '.jar'), name)
    return sdk, binaries, bt, android, apktool


def signing_material(run, binaries):
    """Generate a local project key; never reuse a global identity by default."""
    import secrets
    KEY.mkdir(parents=True, exist_ok=True)
    password, keystore = KEY / 'keystore.pass', KEY / 'sogou-lite.p12'
    if not keystore.exists():
        if password.exists():
            raise SystemExit('An orphan signing password exists; inspect .local/signing first.')
        password.write_text(secrets.token_urlsafe(32), encoding='ascii')
        if os.name != 'nt':
            KEY.chmod(0o700)
            password.chmod(0o600)
        run('keytool', [binaries['keytool'], '-genkeypair', '-keystore', keystore,
            '-storetype', 'PKCS12', '-storepass:file', password, '-keypass:file', password,
            '-alias', 'sogou-lite', '-keyalg', 'RSA', '-keysize', '3072', '-validity', '10000',
            '-dname', 'CN=Offline IME Local Build'])
        if os.name != 'nt':
            keystore.chmod(0o600)
    required_file(password, 'Local signing password')
    run('export-public-cert', [binaries['keytool'], '-exportcert', '-keystore', keystore,
        '-storepass:file', password, '-alias', 'sogou-lite', '-file', KEY / 'signer.der'])
    return password, keystore
