package local.sogoulite.probe;

import com.sogou.speech.butterfly.BFASRJNIInterface;

/** Loads the supplied model without microphone access or changing the installed IME. */
public final class NativeProbe {
    public static void main(String[] args) throws Exception {
        String root = args[0];
        String[] libraries = {
            "libs/offlineasr/arm64-v8a/libc++_shared.so",
            "libs/common/arm64-v8a/libomp.so",
            "libs/common/arm64-v8a/libevalite.so",
            "libs/offlineasr/arm64-v8a/libbutterfly.so"
        };
        for (String lib : libraries) {
            System.load(root + "/" + lib);
            System.out.println("LOADED " + lib);
        }
        long started = System.currentTimeMillis();
        long handle = BFASRJNIInterface.probeInit(root + "/model/butterfly_model");
        // Android may tag native pointers: a valid jlong handle can be negative.
        System.out.println("MODEL_INIT_VALID=" + (handle != 0)
            + " elapsed_ms=" + (System.currentTimeMillis() - started));
        if (handle == 0) throw new IllegalStateException("Model initialization failed");
        BFASRJNIInterface.probeDestroy(handle);
        System.out.println("MODEL_RELEASED");
    }
}
