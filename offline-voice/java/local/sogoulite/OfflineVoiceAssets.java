package local.sogoulite;

import android.content.Context;
import android.os.Handler;
import android.os.Looper;
import android.widget.Toast;
import java.io.*;
import java.lang.reflect.*;
import java.security.MessageDigest;
import java.util.*;
import java.util.zip.*;
import org.json.JSONObject;

/** Bundled, checksum-pinned voice resources. No network code or audio persistence. */
public final class OfflineVoiceAssets {
    private static volatile Context context;
    private static volatile File root;
    private static volatile boolean ready;
    private static volatile boolean started;
    private static volatile String status = "离线语音资源准备中";
    private static Object descriptor, loaded;

    public static synchronized void initialize(Object app) {
        if (started) return;
        try {
            Context c = app instanceof Context ? (Context)app
                : (Context)app.getClass().getMethod("getApplication").invoke(app);
            context = c.getApplicationContext();
            root = new File(context.getFilesDir(), "bundled_offline_voice/v1");
            started = true;
            new Thread(new Runnable() { public void run() {
                try {
                    extract();
                    ready = true;
                    status = "离线语音资源已就绪 · 仅普通话";
                    note("ASSETS_READY");
                } catch (Exception e) {
                    status = "离线语音资源准备失败，请重启后重试";
                    note("ASSETS_ERROR " + e.getClass().getSimpleName());
                }
            }}, "LocalVoiceAssets").start();
        } catch (Exception e) { note("INIT_ERROR " + e.getClass().getSimpleName()); }
    }

    public static boolean isReady() { return ready; }
    public static String status() { return status; }
    public static void notReady() {
        if (context != null) new Handler(Looper.getMainLooper()).post(new Runnable() {
            public void run() { Toast.makeText(context, status, Toast.LENGTH_SHORT).show(); }
        });
    }
    public static int version() { return ready ? 1 : 0; }

    private static byte[] readAll(InputStream in) throws IOException {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        byte[] buf = new byte[8192]; int n;
        while ((n = in.read(buf)) != -1) out.write(buf, 0, n);
        return out.toByteArray();
    }
    private static String digest(File file) throws Exception {
        MessageDigest d = MessageDigest.getInstance("SHA-256");
        try (InputStream in = new FileInputStream(file)) {
            byte[] buf = new byte[65536]; int n;
            while ((n = in.read(buf)) != -1) d.update(buf, 0, n);
        }
        StringBuilder s = new StringBuilder();
        for (byte b : d.digest()) s.append(String.format(Locale.ROOT, "%02x", b & 255));
        return s.toString();
    }
    private static boolean valid(File f, JSONObject info) throws Exception {
        return f.isFile() && f.length() == info.getLong("bytes")
            && digest(f).equals(info.getString("sha256"));
    }
    private static void extract() throws Exception {
        JSONObject manifest;
        try (InputStream in = context.getAssets().open("offline-voice/resource-manifest.json")) {
            manifest = new JSONObject(new String(readAll(in), "UTF-8")).getJSONObject("files");
        }
        if (!root.isDirectory() && !root.mkdirs()) throw new IOException("Cannot create resource directory");
        Set<String> seen = new HashSet<String>();
        String prefix = root.getCanonicalPath() + File.separator;
        try (ZipInputStream zip = new ZipInputStream(context.getAssets().open("offline-voice/resources.zip"))) {
            ZipEntry entry;
            byte[] buf = new byte[65536];
            while ((entry = zip.getNextEntry()) != null) {
                if (entry.isDirectory()) continue;
                String name = entry.getName();
                File file = new File(root, name);
                if (!file.getCanonicalPath().startsWith(prefix) || !manifest.has(name) || !seen.add(name))
                    throw new IOException("Unexpected resource entry");
                JSONObject info = manifest.getJSONObject(name);
                if (!valid(file, info)) {
                    File parent = file.getParentFile();
                    if (!parent.isDirectory() && !parent.mkdirs()) throw new IOException("Cannot create directory");
                    File part = new File(parent, file.getName() + ".partial");
                    try (OutputStream out = new FileOutputStream(part)) {
                        int n; long size = 0;
                        while ((n = zip.read(buf)) != -1) {
                            size += n;
                            if (size > info.getLong("bytes")) throw new IOException("Resource exceeds expected size");
                            out.write(buf, 0, n);
                        }
                    }
                    if (!valid(part, info)) throw new IOException("Resource checksum mismatch");
                    if (file.exists() && !file.delete()) throw new IOException("Cannot replace resource");
                    if (!part.renameTo(file)) throw new IOException("Cannot finalize resource");
                }
                zip.closeEntry();
            }
        }
        if (seen.size() != manifest.length()) throw new IOException("Incomplete resource bundle");
    }

    private static String path(String relative) { return new File(root, relative).getAbsolutePath(); }
    public static synchronized Object descriptor() {
        if (!ready) return null;
        if (descriptor != null) return descriptor;
        try {
            Class<?> type = Class.forName("com.sogou.inputmethod.voiceinput.resource.o");
            descriptor = type.getConstructor(int.class, String.class, String.class, String.class,
                String[].class, String.class, String[].class, String.class,
                String.class, String[].class, String.class).newInstance(
                1, "bundled", "voice_offline_64", path("libs/common/arm64-v8a"),
                new String[]{"libomp.so", "libevalite.so"}, path("libs/offlineasr/arm64-v8a"),
                new String[]{"libc++_shared.so", "libbutterfly.so"}, path("model/butterfly_model"),
                path("libs/punctuator/arm64-v8a"), new String[]{"libpunctuator.so", "libpunctuatorwrapper.so"},
                path("model/punc_model_zh_eng_210702"));
            return descriptor;
        } catch (Exception e) { note("DESCRIPTOR_ERROR " + e.getClass().getSimpleName()); return null; }
    }

    public static synchronized Object load(boolean punctuation) {
        if (!ready) return null;
        if (loaded != null) return loaded;
        try {
            // Keep the same dependency order that passed the standalone device probe.
            for (String lib : new String[]{"libs/offlineasr/arm64-v8a/libc++_shared.so",
                "libs/common/arm64-v8a/libomp.so", "libs/common/arm64-v8a/libevalite.so",
                "libs/offlineasr/arm64-v8a/libbutterfly.so"}) System.load(path(lib));
            boolean punc = false;
            try {
                System.load(path("libs/punctuator/arm64-v8a/libpunctuator.so"));
                System.load(path("libs/punctuator/arm64-v8a/libpunctuatorwrapper.so"));
                punc = true;
            } catch (LinkageError error) { note("PUNCTUATION_LOAD_ERROR " + error.getClass().getSimpleName()); }
            Class<?> type = Class.forName("com.sogou.inputmethod.voiceinput.resource.n");
            Object value = type.getConstructor().newInstance();
            type.getField("a").setInt(value, 1);
            type.getField("b").setBoolean(value, true);
            type.getField("d").setBoolean(value, true);
            type.getField("f").set(value, path("model/butterfly_model"));
            type.getField("g").setBoolean(value, punc);
            loaded = value;
            note("LIBRARIES_READY punctuation=" + punc);
            return value;
        } catch (Exception | LinkageError e) {
            note("LIBRARY_ERROR " + e.getClass().getSimpleName()); return null;
        }
    }

    private static void enumField(Object target, String name, String value) throws Exception {
        Field f = target.getClass().getField(name);
        f.set(target, Enum.valueOf((Class)f.getType(), value));
    }
    public static void configure(Object config) {
        try {
            Object offline = config.getClass().getField("offlineConfig").get(config);
            // Select this before attempting any library work: errors must never enable cloud fallback.
            enumField(offline, "offlineMode", "OFFLINE_ONLY");
            offline.getClass().getField("modelPath").set(offline, path("model/butterfly_model"));
            offline.getClass().getField("mInitByFileDescriptor").setBoolean(offline, false);
            Object resources = load(true);
            Object punc = config.getClass().getField("puncConfig").get(config);
            boolean puncReady = resources != null && resources.getClass().getField("g").getBoolean(resources);
            enumField(punc, "puncMode", puncReady ? "ENABLE" : "DISABLE");
            punc.getClass().getField("modelPath").set(punc, path("model/punc_model_zh_eng_210702"));
            note("ASR_CONFIG offline_only=true libraries=" + (resources != null));
        } catch (Exception e) { note("CONFIG_ERROR " + e.getClass().getSimpleName()); }
    }

    public static void nativeInitResult(long handle) { note("DECODER_INIT valid=" + (handle != 0)); }
    public static void sessionBegin() { note("SESSION_BEGIN"); }
    public static void sessionStop() { note("SESSION_STOP"); }
    public static synchronized void note(String value) {
        try {
            if (context == null) return;
            File dir = context.getExternalFilesDir(null);
            if (dir == null) return;
            File file = new File(dir, "offline-voice.log");
            try (FileWriter out = new FileWriter(file, file.length() < 131072L)) {
                out.write(System.currentTimeMillis() + " " + value + "\n");
            }
        } catch (Exception ignored) { }
    }
}
