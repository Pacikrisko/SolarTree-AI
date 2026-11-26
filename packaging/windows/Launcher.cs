using System;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;

static class Launcher {
    const string Url = "https://solartree-ai.onrender.com/";
    [STAThread]
    static void Main() {
        try {
            foreach (var folder in new[] { Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86),
                                           Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles) }) {
                var edge = Path.Combine(folder, @"Microsoft\Edge\Application\msedge.exe");
                if (File.Exists(edge)) {
                    Process.Start(edge, "--app=" + Url);
                    return;
                }
            }
            Process.Start(new ProcessStartInfo(Url) { UseShellExecute = true });
        } catch (Exception) {
            MessageBox.Show("Не успяхме да отворим Solix.", "Solix");
        }
    }
}
