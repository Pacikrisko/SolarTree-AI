package space.pgknma.solix;

import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.os.IBinder;
import android.widget.Toast;

public class Launcher extends Activity {
    private int getBuildNumber() {
        try { return getPackageManager().getPackageInfo(getPackageName(), 0).versionCode; }
        catch (android.content.pm.PackageManager.NameNotFoundException e) { throw new IllegalStateException(e); }
    }
    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        Intent browser = new Intent(Intent.ACTION_VIEW, Uri.parse("https://solartree-ai.onrender.com/?solixClient=android&build=" + getBuildNumber()));
        Bundle extras = new Bundle();
        extras.putBinder("android.support.customtabs.extra.SESSION", (IBinder) null);
        browser.putExtras(extras);
        browser.putExtra("android.support.customtabs.extra.TOOLBAR_COLOR", 0xff142e25);
        try {
            startActivity(browser);
        } catch (ActivityNotFoundException error) {
            Toast.makeText(this, "Необходим е браузър, за да отвориш Solix.", Toast.LENGTH_LONG).show();
        }
        finish();
    }
}



