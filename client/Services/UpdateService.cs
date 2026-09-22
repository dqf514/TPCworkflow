using System.Diagnostics;
using System.IO;
using System.Text;
using TPCWorkflow.Client.Models;

namespace TPCWorkflow.Client.Services;

public sealed class UpdateCheckResult
{
    public bool UpdateAvailable { get; init; }
    public ClientVersionPayload? Remote { get; init; }
    public string? Message { get; init; }
}

public sealed class UpdateService
{
    private readonly ApiClient _api;

    public UpdateService(ApiClient api)
    {
        _api = api;
    }

    public async Task<UpdateCheckResult> CheckAsync(CancellationToken ct = default)
    {
        var res = await _api.GetAsync<ClientVersionPayload>("client/version", ct).ConfigureAwait(false);
        if (!res.Ok || res.Data is null)
        {
            return new UpdateCheckResult
            {
                UpdateAvailable = false,
                Message = res.Message ?? "无法获取版本信息",
            };
        }

        var remote = res.Data;
        var hasPackage = remote.Downloads?.Setup?.Available == true
                         || remote.Downloads?.Exe?.Available == true
                         || remote.Downloads?.Zip?.Available == true;
        var available = AppVersion.IsRemoteNewer(remote.Version);
        if (!available && !hasPackage)
        {
            return new UpdateCheckResult
            {
                UpdateAvailable = false,
                Remote = remote,
                Message = "服务端尚未发布安装包",
            };
        }

        return new UpdateCheckResult
        {
            UpdateAvailable = available,
            Remote = remote,
        };
    }

    public string? ResolveDownloadPath(ClientVersionPayload remote)
    {
        // 应用内更新优先 exe：与安装目录主程序一致，下载后由 InstallService 覆盖安装
        if (remote.Downloads?.Exe?.Available == true && !string.IsNullOrWhiteSpace(remote.Downloads.Exe.DownloadUrl))
            return remote.Downloads.Exe.DownloadUrl;
        if (remote.Downloads?.Setup?.Available == true && !string.IsNullOrWhiteSpace(remote.Downloads.Setup.DownloadUrl))
            return remote.Downloads.Setup.DownloadUrl;
        return null;
    }

    public async Task DownloadPackageAsync(
        string relativeOrAbsoluteUrl,
        string destinationPath,
        IProgress<double>? progress = null,
        CancellationToken ct = default)
    {
        var dir = Path.GetDirectoryName(destinationPath);
        if (!string.IsNullOrWhiteSpace(dir))
            Directory.CreateDirectory(dir);

        var uri = relativeOrAbsoluteUrl.StartsWith("http", StringComparison.OrdinalIgnoreCase)
            ? relativeOrAbsoluteUrl
            : _api.BaseUrl.TrimEnd('/') + relativeOrAbsoluteUrl;

        await _api.DownloadToFileAsync(uri, destinationPath, progress, ct).ConfigureAwait(false);

        var info = new FileInfo(destinationPath);
        if (!info.Exists || info.Length < 1024 * 64)
            throw new IOException("更新包下载不完整，请重试。");
    }

    /// <summary>
    /// 当前进程退出后启动已下载的安装包。
    /// 安装包会走 InstallService：复制到安装目录、刷新快捷方式并启动新版本。
    /// </summary>
    public void ApplyUpdateAndRestart(string downloadedFilePath)
    {
        if (!File.Exists(downloadedFilePath))
            throw new FileNotFoundException("更新包不存在", downloadedFilePath);

        var info = new FileInfo(downloadedFilePath);
        if (info.Length < 1024 * 64)
            throw new InvalidOperationException("更新包无效或过小，请重新下载。");

        var updateDir = Path.Combine(InstallService.InstallDirectory, "updates");
        Directory.CreateDirectory(updateDir);

        var updaterPath = Path.Combine(updateDir, "apply-update.cmd");
        var logPath = Path.Combine(updateDir, "update.log");
        var pid = Process.GetCurrentProcess().Id;

        var script = new StringBuilder();
        script.AppendLine("@echo off");
        script.AppendLine("chcp 65001 >nul");
        script.AppendLine($"set \"NEWFILE={downloadedFilePath}\"");
        script.AppendLine($"set \"WPID={pid}\"");
        script.AppendLine($"set \"LOGFILE={logPath}\"");
        script.AppendLine("echo [%date% %time%] update start >> \"%LOGFILE%\"");
        script.AppendLine(":waitpid");
        script.AppendLine("timeout /t 1 /nobreak >nul");
        script.AppendLine("tasklist /FI \"PID eq %WPID%\" 2>nul | find /I \"%WPID%\" >nul");
        script.AppendLine("if not errorlevel 1 goto waitpid");
        script.AppendLine(":waitproc");
        script.AppendLine("timeout /t 1 /nobreak >nul");
        script.AppendLine(
            $"tasklist /FI \"IMAGENAME eq {InstallService.ProcessImageName}\" 2>nul | find /I \"{InstallService.ProcessImageName}\" >nul");
        script.AppendLine("if not errorlevel 1 goto waitproc");
        script.AppendLine("timeout /t 1 /nobreak >nul");
        script.AppendLine("if not exist \"%NEWFILE%\" (");
        script.AppendLine("  echo [%date% %time%] package missing >> \"%LOGFILE%\"");
        script.AppendLine("  exit /b 1");
        script.AppendLine(")");
        script.AppendLine("echo [%date% %time%] launching package >> \"%LOGFILE%\"");
        // 启动下载包本身：非安装目录启动会触发 InstallService 覆盖安装并拉起新版本
        script.AppendLine("start \"\" \"%NEWFILE%\"");
        script.AppendLine("if errorlevel 1 (");
        script.AppendLine("  echo [%date% %time%] start failed, fallback copy >> \"%LOGFILE%\"");
        script.AppendLine($"  copy /Y /B \"%NEWFILE%\" \"{InstallService.InstalledExePath}\" >> \"%LOGFILE%\" 2>&1");
        script.AppendLine($"  start \"\" /D \"{InstallService.InstallDirectory}\" \"{InstallService.InstalledExePath}\"");
        script.AppendLine(")");
        script.AppendLine("echo [%date% %time%] done >> \"%LOGFILE%\"");
        script.AppendLine("del \"%~f0\"");

        // 无 BOM，避免 cmd 无法识别首行 @echo off
        File.WriteAllText(updaterPath, script.ToString(), new UTF8Encoding(encoderShouldEmitUTF8Identifier: false));

        var started = Process.Start(new ProcessStartInfo
        {
            FileName = "cmd.exe",
            Arguments = $"/c \"{updaterPath}\"",
            UseShellExecute = true,
            CreateNoWindow = true,
            WindowStyle = ProcessWindowStyle.Hidden,
        });
        if (started is null)
            throw new InvalidOperationException("无法启动更新脚本，请手动运行下载的安装包。");

        if (System.Windows.Application.Current is App app)
            app.RequestFullExit();
        else
            System.Windows.Application.Current.Shutdown();
    }
}
