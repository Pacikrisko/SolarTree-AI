using System;
using System.Diagnostics;
using System.IO;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
using System.Windows.Forms;

static class Launcher {
    static readonly string Url = "https://solartree.pgknma.space/?solixClient=windows&build=" + typeof(Launcher).Assembly.GetName().Version.Revision;
    private delegate bool WindowVisitor(IntPtr window, IntPtr data);
    [DllImport("user32.dll")] static extern bool EnumWindows(WindowVisitor visitor, IntPtr data);
    [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr window);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] static extern int GetWindowText(IntPtr window, StringBuilder text, int capacity);
    [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr window, out int pid);
    [DllImport("user32.dll")] static extern bool ShowWindowAsync(IntPtr window, int command);

    static void MaximizeSolix(HashSet<IntPtr> previous) {
        for (int attempt=0; attempt<100; attempt++) {
            bool found=false;
            EnumWindows(delegate(IntPtr window, IntPtr unused) {
                if(previous.Contains(window) || !IsWindowVisible(window)) return true;
                var title=new StringBuilder(256);
                GetWindowText(window,title,title.Capacity);
                if(!title.ToString().StartsWith("Solix",StringComparison.OrdinalIgnoreCase)) return true;
                int pid;
                GetWindowThreadProcessId(window,out pid);
                try {
                    using(var process=Process.GetProcessById(pid)) {
                        if(process.ProcessName!="msedge") return true;
                    }
                } catch(ArgumentException) { return true; }
                ShowWindowAsync(window,3);
                found=true;
                return false;
            },IntPtr.Zero);
            if(found) return;
            Thread.Sleep(150);
        }
    }
    [STAThread]
    static void Main() {
        try {
            foreach (var folder in new[] { Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86),
                                           Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles) }) {
                var edge = Path.Combine(folder, @"Microsoft\Edge\Application\msedge.exe");
                if (File.Exists(edge)) {
                    var previous=new HashSet<IntPtr>();
                    EnumWindows(delegate(IntPtr window,IntPtr unused){ previous.Add(window); return true; },IntPtr.Zero);
                    Process.Start(new ProcessStartInfo(edge, "--start-fullscreen --start-maximized --app=\"" + Url + "\"") {
                        WindowStyle = ProcessWindowStyle.Maximized
                    });
                    MaximizeSolix(previous);
                    return;
                }
            }
            Process.Start(new ProcessStartInfo(Url) { UseShellExecute = true, WindowStyle = ProcessWindowStyle.Maximized });
        } catch (Exception) {
            MessageBox.Show("Не успяхме да отворим Solix.", "Solix");
        }
    }
}




