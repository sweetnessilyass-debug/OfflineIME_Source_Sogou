package local.sogoulite;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.os.Bundle;
import android.provider.Settings;
import android.view.View;
import android.view.inputmethod.InputMethodManager;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

public class LiteActivity extends Activity {
    private LinearLayout content;
    public static void open(Activity caller) {
        caller.startActivity(new Intent(caller, LiteActivity.class));
        caller.finish();
    }
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        OfflineVoiceAssets.initialize(this);
        setTitle("搜狗离线语音");
        getWindow().setStatusBarColor(Color.rgb(241,245,249));
        getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR);
        ScrollView scroll = new ScrollView(this);
        content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        int pad = (int)(20 * getResources().getDisplayMetrics().density);
        content.setPadding(pad,pad,pad,pad);
        content.setBackgroundColor(Color.rgb(248,250,252));
        scroll.addView(content);
        text("搜狗离线语音",26);
        text("本地输入与普通话语音 · 20.17.0 / Lite 0.2\n语音资源已内置，首次使用无需下载。",15);
        button("1. 启用输入法", new View.OnClickListener(){public void onClick(View v){startActivity(new Intent(Settings.ACTION_INPUT_METHOD_SETTINGS));}});
        button("2. 切换到搜狗离线语音", new View.OnClickListener(){public void onClick(View v){((InputMethodManager)getSystemService(INPUT_METHOD_SERVICE)).showInputMethodPicker();}});
        button("3. 允许麦克风用于离线语音", new View.OnClickListener(){public void onClick(View v){if(android.os.Build.VERSION.SDK_INT >= 23) requestPermissions(new String[]{"android.permission.RECORD_AUDIO"},71);}});
        button("检查离线语音资源", new View.OnClickListener(){public void onClick(View v){Toast.makeText(LiteActivity.this,OfflineVoiceAssets.status(),Toast.LENGTH_LONG).show();}});
        text("试打区",19);
        EditText test = new EditText(this);
        test.setHint("点这里试打中文、数字和标点");
        test.setSingleLine(false);
        test.setMinLines(3);
        test.setTextSize(19);
        content.addView(test,new LinearLayout.LayoutParams(-1,-2));
        text("输入设置",19);
        setting("输入设置","com.sogou.imskit.feature.settings.activity.InputSettings");
        setting("模糊音设置","com.sogou.imskit.feature.settings.FuzzyCodeSettings");
        setting("键盘设置","com.sogou.imskit.feature.settings.activity.KeyboardSettings");
        setting("剪贴板设置","com.sogou.clipboard.setting.ClipboardSettingActivity");
        setting("常用语设置","com.sogou.shortcutphrase.setting.PhraseSettingActivity");
        text("已移除联网权限。语音仅在手机本地识别普通话，不支持云端回退。广告入口、皮肤商城、账号、推送、云候选与在线更新保持关闭。\n非官方实验版；请先验证识别和上屏。",13);
        content.setFocusableInTouchMode(true);
        content.requestFocus();
        setContentView(scroll);
    }
    private void setting(String title,final String cls) {
        button(title,new View.OnClickListener(){public void onClick(View v){
            try { startActivity(new Intent().setClassName(getPackageName(),cls)); }
            catch (Exception e) { Toast.makeText(LiteActivity.this,"此项请从键盘工具栏调整",Toast.LENGTH_SHORT).show(); }
        }});
    }
    private void text(String value,int sp) {
        TextView view = new TextView(this); view.setText(value); view.setTextSize(sp);
        view.setTextColor(Color.rgb(30,41,59)); view.setPadding(0,14,0,14);
        content.addView(view,new LinearLayout.LayoutParams(-1,-2));
    }
    private void button(String title,View.OnClickListener listener) {
        Button b = new Button(this); b.setText(title); b.setAllCaps(false); b.setOnClickListener(listener);
        content.addView(b,new LinearLayout.LayoutParams(-1,-2));
    }
}
