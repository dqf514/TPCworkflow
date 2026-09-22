using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;

namespace TPCWorkflow.Client.Services;

/// <summary>
/// 将绿色单文件“安装”到用户目录，并创建桌面/开始菜单快捷方式。
/// </summary>
public static class InstallService
{
    public const string ShortcutName = "IMC 工作台";
    public const string ProcessImageName = "TPCWorkflow.Client.exe";

    public static string InstallDirectory => Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
        "TPCWorkflow");

    public static string InstalledExePath => Path.Combine(InstallDirectory, ProcessImageName);

    public static bool IsRunningFromInstallLocation()
    {
        var current = Environment.ProcessPath;
        if (string.IsNullOrWhiteSpace(current))
            return true;
        return string.Equals(
            Path.GetFullPath(current),
            Path.GetFullPath(InstalledExePath),
            StringComparison.OrdinalIgnoreCase);
    }

    /// <summary>
    /// 若从下载目录等位置启动，则复制到安装目录、创建快捷方式并重启。
    /// </summary>
    public static bool EnsureInstalledAndRelaunchIfNeeded()
    {
        if (IsRunningFromInstallLocation())
        {
            EnsureShortcuts();
            return false;
        }

        var current = Environment.ProcessPath;
        if (string.IsNullOrWhiteSpace(current) || !File.Exists(current))
            return false;

        Directory.CreateDirectory(InstallDirectory);
        File.Copy(current, InstalledExePath, overwrite: true);
        EnsureShortcuts();
        LaunchInstalled();

        if (System.Windows.Application.Current is App app)
            app.RequestFullExit();
        else
            System.Windows.Application.Current.Shutdown();

        return true;
    }

    public static void LaunchInstalled()
    {
        Process.Start(new ProcessStartInfo
        {
            FileName = InstalledExePath,
            WorkingDirectory = InstallDirectory,
            UseShellExecute = true,
        });
    }

    public static string ResolveUpdateTargetPath()
    {
        if (File.Exists(InstalledExePath))
            return InstalledExePath;
        return Environment.ProcessPath ?? InstalledExePath;
    }

    public static void EnsureShortcuts()
    {
        if (!File.Exists(InstalledExePath))
            return;

        var desktop = Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory);
        var startMenu = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.StartMenu),
            "Programs");
        Directory.CreateDirectory(startMenu);

        CreateShortcut(Path.Combine(desktop, ShortcutName + ".lnk"));
        CreateShortcut(Path.Combine(startMenu, ShortcutName + ".lnk"));
    }

    private static void CreateShortcut(string shortcutPath)
    {
        try
        {
            var target = Path.GetFullPath(InstalledExePath);
            var dir = Path.GetDirectoryName(shortcutPath);
            if (!string.IsNullOrWhiteSpace(dir))
                Directory.CreateDirectory(dir);

            var shellType = Type.GetTypeFromProgID("WScript.Shell");
            if (shellType is null)
                return;

            dynamic shell = Activator.CreateInstance(shellType)!;
            dynamic link = shell.CreateShortcut(shortcutPath);
            link.TargetPath = target;
            link.WorkingDirectory = InstallDirectory;
            link.IconLocation = target + ",0";
            link.Description = ShortcutName;
            link.Save();

            if (Marshal.IsComObject(shell))
                Marshal.ReleaseComObject(shell);
        }
        catch
        {
            /* 快捷方式创建失败不影响主流程 */
        }
    }
}
