using System.IO;
using System.Windows;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using TPCWorkflow.Client.Models;
using TPCWorkflow.Client.Services;

namespace TPCWorkflow.Client;

public partial class LoginWindow : Window
{
    private AppPreferences _prefs;
    private SavedLoginCredentials _saved;
    private string _captchaId = "";
    private bool _emailMode;

    private AuthService AuthSvc => ((App)System.Windows.Application.Current).Auth!;

    public LoginWindow(AuthService auth, AppPreferences prefs, SavedLoginCredentials saved)
    {
        InitializeComponent();
        AppIconHelper.ApplyWindowIcon(this);
        _prefs = prefs;
        _saved = saved;
        Loaded += async (_, _) => await InitializeAsync();
    }

    public UserProfile? LoggedInUser { get; private set; }

    private async Task InitializeAsync()
    {
        RestoreSavedCredentials();
        await CheckServerAsync();
        await LoadBrandingAsync();
        if (!_emailMode)
            await ReloadCaptchaAsync();
    }

    private void RestoreSavedCredentials()
    {
        RememberUsernameCheck.IsChecked = _saved.RememberUsername;
        RememberPasswordCheck.IsChecked = _saved.RememberPassword;
        AutoLoginCheck.IsChecked = _saved.AutoLogin;

        if (_saved.RememberUsername && !string.IsNullOrWhiteSpace(_saved.Username))
            UsernameBox.Text = _saved.Username;
        if (!string.IsNullOrWhiteSpace(_saved.Email))
            EmailBox.Text = _saved.Email;
        RememberEmailCheck.IsChecked = _saved.RememberEmail || !string.IsNullOrWhiteSpace(_saved.Email);
        if (_saved.RememberPassword)
        {
            var pwd = _saved.GetPassword();
            if (!string.IsNullOrEmpty(pwd))
                PasswordBox.Password = pwd;
        }
    }

    private void PersistSavedCredentials()
    {
        _saved.RememberUsername = RememberUsernameCheck.IsChecked == true;
        _saved.RememberEmail = RememberEmailCheck.IsChecked == true;
        _saved.RememberPassword = RememberPasswordCheck.IsChecked == true;
        _saved.AutoLogin = AutoLoginCheck.IsChecked == true;

        if (_saved.RememberUsername)
            _saved.Username = UsernameBox.Text.Trim();
        else
            _saved.Username = null;

        if (_saved.RememberEmail)
            _saved.Email = EmailBox.Text.Trim();
        else
            _saved.Email = null;

        if (_saved.RememberPassword && !_emailMode)
            _saved.SetPassword(PasswordBox.Password);
        else
            _saved.ClearPassword();

        _saved.Save();
    }

    private async Task CheckServerAsync()
    {
        var app = (App)System.Windows.Application.Current;
        var health = await app.Api!.HealthCheckAsync();
        if (health.Ok)
            return;
        ShowError(health.Message);
    }

    private async Task LoadBrandingAsync()
    {
        var res = await AuthSvc.LoadLoginMethodsAsync();
        if (!res.Ok || res.Data is null)
            return;
        if (!string.IsNullOrWhiteSpace(res.Data.AppName))
            AppNameText.Text = res.Data.AppName;
        CompanyText.Text = res.Data.CompanyName ?? "";
    }

    private void PwdTab_Click(object sender, RoutedEventArgs e) => SwitchMode(false);

    private void EmailTab_Click(object sender, RoutedEventArgs e) => SwitchMode(true);

    private void SwitchMode(bool email)
    {
        _emailMode = email;
        PasswordPanel.Visibility = email ? Visibility.Collapsed : Visibility.Visible;
        EmailPanel.Visibility = email ? Visibility.Visible : Visibility.Collapsed;
        CaptchaPanel.Visibility = email ? Visibility.Collapsed : Visibility.Visible;
        RememberUsernameCheck.Visibility = email ? Visibility.Collapsed : Visibility.Visible;
        RememberEmailCheck.Visibility = email ? Visibility.Visible : Visibility.Collapsed;
        RememberPasswordCheck.Visibility = email ? Visibility.Collapsed : Visibility.Visible;
        AutoLoginCheck.Visibility = email ? Visibility.Collapsed : Visibility.Visible;
        var brand = (System.Windows.Media.Brush)FindResource("BrandBrush");
        var muted = (System.Windows.Media.Brush)FindResource("TextSecondaryBrush");
        PwdTabBtn.Background = email ? System.Windows.Media.Brushes.Transparent : brand;
        PwdTabBtn.Foreground = email ? muted : System.Windows.Media.Brushes.White;
        EmailTabBtn.Background = email ? brand : System.Windows.Media.Brushes.Transparent;
        EmailTabBtn.Foreground = email ? System.Windows.Media.Brushes.White : muted;
        ClearError();
        if (!email && CaptchaImage.Source is null)
            _ = ReloadCaptchaAsync();
    }

    private void SettingsGear_Click(object sender, RoutedEventArgs e)
    {
        var dlg = new ServerSettingsWindow(_prefs) { Owner = this };
        if (dlg.ShowDialog() != true)
            return;
        _prefs.ServerBaseUrl = dlg.ServerUrl;
        _prefs.Save();
        ((App)System.Windows.Application.Current).ApplyServerUrl(dlg.ServerUrl);
        _ = InitializeAsync();
    }

    private void DragArea_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
    {
        if (e.ButtonState == MouseButtonState.Pressed)
            DragMove();
    }

    private void CloseButton_Click(object sender, RoutedEventArgs e) => Close();

    private async Task ReloadCaptchaAsync()
    {
        ClearError();
        CaptchaImage.Source = null;
        CaptchaPlaceholder.Visibility = Visibility.Visible;

        var res = await AuthSvc.LoadCaptchaAsync();
        if (!res.Ok || res.Data is null)
        {
            ShowError(res.Message);
            return;
        }
        _captchaId = res.Data.CaptchaId;
        try
        {
            var src = res.Data.Image;
            if (!src.StartsWith("data:image", StringComparison.OrdinalIgnoreCase))
            {
                ShowError("验证码格式异常");
                return;
            }
            var comma = src.IndexOf(',');
            var b64 = comma >= 0 ? src[(comma + 1)..] : src;
            var bytes = Convert.FromBase64String(b64);
            using var ms = new MemoryStream(bytes);
            var img = new BitmapImage();
            img.BeginInit();
            img.CacheOption = BitmapCacheOption.OnLoad;
            img.StreamSource = ms;
            img.EndInit();
            img.Freeze();
            CaptchaImage.Source = img;
            CaptchaPlaceholder.Visibility = Visibility.Collapsed;
        }
        catch
        {
            ShowError("验证码图片加载失败");
        }
    }

    private async void CaptchaImage_Click(object sender, MouseButtonEventArgs e)
    {
        await ReloadCaptchaAsync();
    }

    private async void SendCode_Click(object sender, RoutedEventArgs e)
    {
        ClearError();
        SendCodeBtn.IsEnabled = false;
        try
        {
            var res = await AuthSvc.SendEmailCodeAsync(EmailBox.Text.Trim());
            if (!res.Ok)
            {
                ShowError(res.Message);
                return;
            }
            ShowInfo("验证码已发送至邮箱");
        }
        finally
        {
            SendCodeBtn.IsEnabled = true;
        }
    }

    private async void LoginButton_Click(object sender, RoutedEventArgs e)
    {
        await DoLoginAsync();
    }

    private async void CaptchaBox_KeyDown(object sender, System.Windows.Input.KeyEventArgs e)
    {
        if (e.Key == Key.Enter)
            await DoLoginAsync();
    }

    private async Task DoLoginAsync()
    {
        ClearError();
        LoginButton.IsEnabled = false;
        try
        {
            ApiResult<UserProfile> res = _emailMode
                ? await AuthSvc.LoginEmailAsync(
                    EmailBox.Text.Trim(),
                    EmailCodeBox.Text.Trim())
                : await AuthSvc.LoginAsync(
                    UsernameBox.Text.Trim(),
                    PasswordBox.Password,
                    _captchaId,
                    CaptchaBox.Text.Trim());

            if (!res.Ok || res.Data is null)
            {
                ShowError(res.Message);
                if (!_emailMode)
                    await ReloadCaptchaAsync();
                return;
            }

            PersistSavedCredentials();
            LoggedInUser = res.Data;
            DialogResult = true;
            // 先结束模态循环，再由 App 延迟打开主窗
            Close();
            return;
        }
        finally
        {
            LoginButton.IsEnabled = true;
        }
    }

    private void ShowError(string message)
    {
        ErrorText.Foreground = new SolidColorBrush(System.Windows.Media.Color.FromRgb(0xD0, 0x30, 0x50));
        ErrorText.Text = message;
    }

    private void ShowInfo(string message)
    {
        ErrorText.Foreground = (System.Windows.Media.Brush)FindResource("BrandBrush")!;
        ErrorText.Text = message;
    }

    private void ClearError() => ErrorText.Text = "";
}
