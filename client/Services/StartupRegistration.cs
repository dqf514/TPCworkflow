using System.IO;
using Microsoft.Win32;

namespace TPCWorkflow.Client.Services;

public static class StartupRegistration
{
    private const string RunKeyPath = @"Software\Microsoft\Windows\CurrentVersion\Run";
    private const string AppName = "TPCWorkflowClient";
    private const string ProtocolName = "tpcworkflow";

    public static void SetAutoStart(bool enabled)
    {
        using var key = Registry.CurrentUser.OpenSubKey(RunKeyPath, writable: true);
        if (key is null)
            return;
        if (enabled)
        {
            var exe = File.Exists(InstallService.InstalledExePath)
                ? InstallService.InstalledExePath
                : Environment.ProcessPath ?? System.Diagnostics.Process.GetCurrentProcess().MainModule?.FileName;
            if (!string.IsNullOrWhiteSpace(exe))
                key.SetValue(AppName, $"\"{exe}\"");
        }
        else
        {
            key.DeleteValue(AppName, throwOnMissingValue: false);
        }
    }

    public static void RegisterProtocol()
    {
        var exe = File.Exists(InstallService.InstalledExePath)
            ? InstallService.InstalledExePath
            : Environment.ProcessPath ?? "";
        if (string.IsNullOrWhiteSpace(exe))
            return;

        using var classes = Registry.CurrentUser.CreateSubKey(@"Software\Classes\" + ProtocolName);
        classes?.SetValue("", "URL:TPC Workflow Protocol");
        classes?.SetValue("URL Protocol", "");
        using var icon = classes?.CreateSubKey("DefaultIcon");
        icon?.SetValue("", $"\"{exe}\",0");
        using var command = classes?.CreateSubKey(@"shell\open\command");
        command?.SetValue("", $"\"{exe}\" \"%1\"");
    }

    public static string? ParseProtocolArg(string[] args)
    {
        foreach (var arg in args)
        {
            if (!arg.StartsWith("tpcworkflow://", StringComparison.OrdinalIgnoreCase))
                continue;
            var uri = arg["tpcworkflow://".Length..];
            if (uri.StartsWith("task/", StringComparison.OrdinalIgnoreCase))
                return "/tasks/" + uri["task/".Length..].Trim('/');
            if (uri.StartsWith("instance/", StringComparison.OrdinalIgnoreCase))
                return "/instances/" + uri["instance/".Length..].Trim('/');
            if (uri.StartsWith("open/", StringComparison.OrdinalIgnoreCase))
                return "/" + uri["open/".Length..].Trim('/');
            return "/" + uri.Trim('/');
        }
        return null;
    }
}

public static class SingleInstanceManager
{
    private const string MutexName = "Global\\TPCWorkflow.Client.SingleInstance";
    private static Mutex? _mutex;

    public static bool TryAcquire()
    {
        _mutex = new Mutex(true, MutexName, out var created);
        return created;
    }

    public static void SignalExistingInstance(string? navPath)
    {
        if (!string.IsNullOrWhiteSpace(navPath))
            PendingNavigation.Write(navPath);
        NativeMethods.BringExistingToFront();
    }

    public static void Release()
    {
        _mutex?.ReleaseMutex();
        _mutex?.Dispose();
        _mutex = null;
    }
}

internal static class NativeMethods
{
    [System.Runtime.InteropServices.DllImport("user32.dll")]
    private static extern bool SetForegroundWindow(IntPtr hWnd);

    [System.Runtime.InteropServices.DllImport("user32.dll", CharSet = System.Runtime.InteropServices.CharSet.Unicode)]
    private static extern IntPtr FindWindow(string? lpClassName, string? lpWindowName);

    public static void BringExistingToFront()
    {
        var hwnd = FindWindow(null, "TPC 工作台");
        if (hwnd != IntPtr.Zero)
            SetForegroundWindow(hwnd);
    }
}
