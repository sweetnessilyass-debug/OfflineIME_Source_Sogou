package local.sogoulite;

import java.lang.reflect.Method;
import java.util.Iterator;
import java.util.List;
import android.util.Log;
import android.view.View;

public final class OfflinePolicy {
    private OfflinePolicy() {}
    public static void trimInputSettings(Object fragment) {
        try {
            Object manager = fragment.getClass().getMethod("getPreferenceManager").invoke(fragment);
            Method find = manager.getClass().getMethod("findPreference", CharSequence.class);
            for (String key : new String[]{"pref_cloudinput_usr_switch", "smart_input"}) {
                Object item = find.invoke(manager, key);
                if (item != null) item.getClass().getMethod("setVisible", boolean.class).invoke(item, false);
            }
        } catch (ReflectiveOperationException e) {
            Log.e("SogouLite", "Preference filtering failed", e);
        }
    }
    public static void trimNavigation(View root) {
        String[] ids = {"cne", "cnl", "cno", "cnk", "cnj", "cnh", "cng"};
        for (String name : ids) {
            int id = root.getResources().getIdentifier(name, "id", root.getContext().getPackageName());
            View item = root.findViewById(id);
            if (item != null) {
                item.setVisibility(View.GONE);
                item.setClickable(false);
                item.setImportantForAccessibility(View.IMPORTANT_FOR_ACCESSIBILITY_NO_HIDE_DESCENDANTS);
            }
        }
    }
    public static boolean allowedTool(int id) {
        switch (id) {
            case 3: case 6: case 8: case 10: case 11: case 15: case 19:
            case 21: case 22: case 23: case 24: case 26: case 27:
            case 57: case 63: case 64: case 65: case 99: case 100:
                return true;
            default: return false;
        }
    }
    // The pipeline supplies mutable ArrayLists of ToolKitItem instances.
    public static void filterTools(Object model) {
        if (model == null) return;
        try {
            filterList((List<?>) model.getClass().getMethod("a").invoke(model));
            if (model.getClass().getName().equals("com.sohu.inputmethod.imefuncustom.toolbar.model.b")) {
                filterList((List<?>) model.getClass().getMethod("d").invoke(model));
            }
        } catch (ReflectiveOperationException e) {
            Log.e("SogouLite", "Tool filtering failed", e);
        }
    }
    private static void filterList(List<?> items) throws ReflectiveOperationException {
        if (items == null) return;
        Iterator<?> it = items.iterator();
        while (it.hasNext()) {
            Object item = it.next();
            Method idMethod = item.getClass().getMethod("c");
            int id = ((Integer) idMethod.invoke(item)).intValue();
            if (!allowedTool(id)) it.remove();
        }
    }
}
