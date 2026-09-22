using System.Windows;
using TPCWorkflow.Client.Services;

namespace TPCWorkflow.Client;

public partial class ServerSettingsWindow : Window
{
    public ServerSettingsWindow(AppPreferences prefs)
    {
        InitializeComponent();
        ServerBox.Text = prefs.ServerBaseUrl;
    }

    public string ServerUrl { get; private set; } = "";

    private void Save_Click(object sender, RoutedEventArgs e)
    {
        var url = ServerBox.Text.Trim().TrimEnd('/');
        if (string.IsNullOrWhiteSpace(url) || !Uri.TryCreate(url, UriKind.Absolute, out _))
        {
            System.Windows.MessageBox.Show(this, "请输入有效的 https 地址", "提示",
                MessageBoxButton.OK, MessageBoxImage.Warning);
            return;
        }
        ServerUrl = url;
        DialogResult = true;
        Close();
    }

    private void Cancel_Click(object sender, RoutedEventArgs e)
    {
        DialogResult = false;
        Close();
    }
}
