using System.IO;
using System.Windows;
using TPCWorkflow.Client.Models;
using TPCWorkflow.Client.Services;

namespace TPCWorkflow.Client;

public partial class UpdateWindow : Window
{
    private readonly UpdateService _updates;
    private readonly AppPreferences _prefs;
    private readonly ClientVersionPayload _remote;
    private CancellationTokenSource? _cts;

    public UpdateWindow(UpdateService updates, AppPreferences prefs, ClientVersionPayload remote)
    {
        InitializeComponent();
        _updates = updates;
        _prefs = prefs;
        _remote = remote;

        TitleText.Text = remote.Mandatory ? "需要更新到最新版本" : "发现新版本";
        VersionText.Text = $"当前版本 {AppVersion.Current} → 最新版本 {remote.Version}";
        NotesText.Text = string.IsNullOrWhiteSpace(remote.ReleaseNotes)
            ? "建议更新以获得最新功能与修复。"
            : remote.ReleaseNotes;
        LaterButton.Visibility = remote.Mandatory ? Visibility.Collapsed : Visibility.Visible;
    }

    private void LaterButton_Click(object sender, RoutedEventArgs e)
    {
        _prefs.SkippedUpdateVersion = _remote.Version;
        _prefs.Save();
        DialogResult = false;
        Close();
    }

    private async void UpdateButton_Click(object sender, RoutedEventArgs e)
    {
        var downloadPath = _updates.ResolveDownloadPath(_remote);
        if (string.IsNullOrWhiteSpace(downloadPath))
        {
            System.Windows.MessageBox.Show(this, "服务端未提供可下载的安装包。", "更新失败",
                MessageBoxButton.OK, MessageBoxImage.Warning);
            return;
        }

        UpdateButton.IsEnabled = false;
        LaterButton.IsEnabled = false;
        ProgressBar.Visibility = Visibility.Visible;
        StatusText.Visibility = Visibility.Visible;
        StatusText.Text = "正在下载更新包…";

        var updateDir = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "TPCWorkflow",
            "updates");
        Directory.CreateDirectory(updateDir);
        var pendingFile = Path.Combine(updateDir, "TPCWorkflow-Update.pending.exe");

        _cts = new CancellationTokenSource();
        try
        {
            var progress = new Progress<double>(p =>
            {
                ProgressBar.Value = p;
                StatusText.Text = $"正在下载… {p:0}%";
            });
            await _updates.DownloadPackageAsync(downloadPath, pendingFile, progress, _cts.Token);
            StatusText.Text = "下载完成，正在启动安装…";
            _updates.ApplyUpdateAndRestart(pendingFile);
        }
        catch (OperationCanceledException)
        {
            StatusText.Text = "已取消下载";
            UpdateButton.IsEnabled = true;
            LaterButton.IsEnabled = !_remote.Mandatory;
        }
        catch (Exception ex)
        {
            System.Windows.MessageBox.Show(this, $"更新失败：{ex.Message}", "更新失败",
                MessageBoxButton.OK, MessageBoxImage.Error);
            UpdateButton.IsEnabled = true;
            LaterButton.IsEnabled = !_remote.Mandatory;
            ProgressBar.Visibility = Visibility.Collapsed;
        }
    }

    protected override void OnClosed(EventArgs e)
    {
        _cts?.Cancel();
        _cts?.Dispose();
        base.OnClosed(e);
    }
}
