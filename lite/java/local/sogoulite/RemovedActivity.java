package local.sogoulite;
import android.app.Activity;
import android.os.Bundle;
public final class RemovedActivity extends Activity {
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        setResult(RESULT_CANCELED);
        finish();
    }
}
