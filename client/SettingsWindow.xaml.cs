using System.Windows;
using TPCWorkflow.Client.Services;

namespace TPCWorkflow.Client;

public partial class SettingsWindow : Window
{
    private readonly AppPreferences _prefs;
    private readonly UpdateService? _updates;

    public SettingsWindow(AppPreferences prefs, UpdateService? updates = null)
    {
        InitializeComponent();
        _prefs = prefs;
        _updates = updates;
        ServerBox.Text = prefs.ServerBaseUrl;
        DeviceBox.Text = prefs.DeviceName;
        TrayCheck.IsChecked = prefs.MinimizeToTray;
        NotifyCheck.IsChecked = prefs.EnableNotifications;
        AutoStartCheck.IsChecked = prefs.AutoStart;
        AutoUpdateCheck.IsChecked = prefs.AutoCheckUpdates;
        VersionInfoText.Text = $"当前版本：{AppVersion.Current}";
    }

    public AppPreferences Result { get; private set; } = new();
    public bool ServerChanged { get; private set; }

    private void Save_Click(object sender, RoutedEventArgs e)
    {
        var server = ServerBox.Text.Trim().TrimEnd('/');
        if (string.IsNullOrWhiteSpace(server))
        {
            System.Windows.MessageBox.Show(this, "请输入服务器地址", "提示", MessageBoxButton.OK, MessageBoxImage.Warning);
            return;
        }
        ServerChanged = !string.Equals(server, _prefs.ServerBaseUrl, StringComparison.OrdinalIgnoreCase);
        Result = new AppPreferences
        {
            ServerBaseUrl = server,
            DeviceName = string.IsNullOrWhiteSpace(DeviceBox.Text) ? "Windows 工作台" : DeviceBox.Text.Trim(),
            MinimizeToTray = TrayCheck.IsChecked == true,
            EnableNotifications = NotifyCheck.IsChecked == true,
            AutoStart = AutoStartCheck.IsChecked == true,
            EnableSound = _prefs.EnableSound,
            AutoCheckUpdates = AutoUpdateCheck.IsChecked == true,
            SkippedUpdateVersion = _prefs.SkippedUpdateVersion,
            LastUpdateCheckAt = _prefs.LastUpdateCheckAt,
        };
        Result.Save();
        StartupRegistration.SetAutoStart(Result.AutoStart);
        DialogResult = true;
        Close();
    }

    private async void CheckUpdate_Click(object sender, RoutedEventArgs e)
    {
        if (_updates is null)
        {
            System.Windows.MessageBox.Show(this, "更新服务未就绪", "提示", MessageBoxButton.OK, MessageBoxImage.Information);
            return;
        }

        try
        {
            var result = await _updates.CheckAsync();
            if (!result.UpdateAvailable || result.Remote is null)
            {
                System.Windows.MessageBox.Show(this,
                    result.Message ?? $"当前已是最新版本（{AppVersion.Current}）",
                    "检查更新", MessageBoxButton.OK, MessageBoxImage.Information);
                return;
            }

            var dlg = new UpdateWindow(_updates, _prefs, result.Remote) { Owner = this };
            dlg.ShowDialog();
        }
        catch (Exception ex)
        {
            System.Windows.MessageBox.Show(this, $"检查更新失败：{ex.Message}", "检查更新",
                MessageBoxButton.OK, MessageBoxImage.Warning);
        }
    }

    private void Cancel_Click(object sender, RoutedEventArgs e)
    {
        DialogResult = false;
        Close();
    }
}
