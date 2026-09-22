using System.Windows;
using System.Windows.Threading;
using TPCWorkflow.Client.Services;

namespace TPCWorkflow.Client;

public partial class App : System.Windows.Application
{
    public AppPreferences Preferences { get; private set; } = new();
    public LocalAuthState AuthState { get; private set; } = new();
    public SavedLoginCredentials SavedLogin { get; private set; } = new();
    public ApiClient? Api { get; private set; }
    public AuthService? Auth { get; private set; }
    public ClientService? Client { get; private set; }
    public NotificationService Notifications { get; } = new();

    private MainWindow? _mainWindow;
    private string? _startupNavPath;
    private bool _forceExit;
    private bool _handoffToLogin;

    protected override async void OnStartup(StartupEventArgs e)
    {
        // 登录窗关闭后、主窗显示前，不能让应用因「无窗口」而自动退出
        ShutdownMode = ShutdownMode.OnExplicitShutdown;

        base.OnStartup(e);
        if (InstallService.EnsureInstalledAndRelaunchIfNeeded())
            return;

        StartupRegistration.RegisterProtocol();
        _startupNavPath = StartupRegistration.ParseProtocolArg(e.Args);

        if (!SingleInstanceManager.TryAcquire())
        {
            SingleInstanceManager.SignalExistingInstance(_startupNavPath);
            Shutdown();
            return;
        }

        Preferences = AppPreferences.Load();
        AuthState = LocalAuthState.Load();
        SavedLogin = SavedLoginCredentials.Load();
        if (!string.IsNullOrWhiteSpace(AuthState.ServerBaseUrl))
            Preferences.ServerBaseUrl = AuthState.ServerBaseUrl.TrimEnd('/');

        Api = new ApiClient(Preferences.ServerBaseUrl);
        Auth = new AuthService(Api, Preferences, AuthState);
        Client = new ClientService(Api);

        // 自动登录：设备令牌静默续期（免验证码）
        if (SavedLogin.AutoLogin && Auth.IsLoggedIn && await Auth.TryRefreshAsync())
        {
            ShowMain(_startupNavPath);
            return;
        }

        ShowLogin();
    }

    protected override void OnExit(ExitEventArgs e)
    {
        SingleInstanceManager.Release();
        base.OnExit(e);
    }

    public void ShowLogin()
    {
        if (Auth is null)
            return;
        var login = new LoginWindow(Auth, Preferences, SavedLogin);
        var ok = login.ShowDialog();
        if (ok == true)
            ScheduleShowMain(_startupNavPath);
        else if (!_forceExit)
            Shutdown();
    }

    /// <summary>
    /// 模态登录窗关闭后立即 Show 主窗，在 WPF 下主窗可能不显示；延迟到消息队列空闲后再打开。
    /// </summary>
    private void ScheduleShowMain(string? navPath)
    {
        var path = navPath;
        _startupNavPath = null;
        Dispatcher.BeginInvoke(() => ShowMain(path), DispatcherPriority.ApplicationIdle);
    }

    public void ShowMain(string? navPath = null)
    {
        if (Api is null || Auth is null || Client is null)
            return;

        if (_mainWindow is not null && !_mainWindow.IsLoaded)
        {
            _mainWindow.Closed -= OnMainWindowClosed;
            _mainWindow = null;
        }

        if (_mainWindow is null)
        {
            _mainWindow = new MainWindow(Api, Auth, Client, Preferences, Notifications);
            MainWindow = _mainWindow;
            _mainWindow.Closed += OnMainWindowClosed;
        }

        _mainWindow.Show();
        _mainWindow.WindowState = WindowState.Normal;
        _mainWindow.Visibility = Visibility.Visible;
        _mainWindow.ShowInTaskbar = true;
        _mainWindow.Topmost = true;
        _mainWindow.Activate();
        _mainWindow.Focus();
        _mainWindow.Topmost = false;

        if (!string.IsNullOrWhiteSpace(navPath))
            _mainWindow.NavigateToPath(navPath);
        else
        {
            var pending = PendingNavigation.ReadAndClear();
            if (!string.IsNullOrWhiteSpace(pending))
                _mainWindow.NavigateToPath(pending);
        }
    }

    private void OnMainWindowClosed(object? sender, EventArgs e)
    {
        _mainWindow = null;
        if (_handoffToLogin)
        {
            _handoffToLogin = false;
            ShowLogin();
            return;
        }
        if (!_forceExit)
            Shutdown();
    }

    public void BeginReloginHandoff()
    {
        _handoffToLogin = true;
        if (_mainWindow is null)
        {
            _handoffToLogin = false;
            ShowLogin();
            return;
        }
        _mainWindow.ForceClose();
        _mainWindow.Close();
    }

    public void RequestFullExit()
    {
        _forceExit = true;
        _forceCloseMain();
        Shutdown();
    }

    private void _forceCloseMain()
    {
        _forceExit = true;
        if (_mainWindow is not null)
        {
            _mainWindow.ForceClose();
            _mainWindow.Close();
            _mainWindow = null;
        }
    }

    public void ReloadServicesAfterSettings(AppPreferences prefs, bool serverChanged)
    {
        Preferences = prefs;
        if (serverChanged)
        {
            AuthState.Clear();
            Api?.UpdateBaseUrl(prefs.ServerBaseUrl);
            Auth = new AuthService(Api!, prefs, AuthState);
            Client = new ClientService(Api!);
            _forceCloseMain();
            ShowLogin();
            return;
        }
        if (Auth is not null)
            Auth.UpdatePreferences(prefs);
    }

    public void ApplyServerUrl(string serverUrl)
    {
        var url = serverUrl.Trim().TrimEnd('/');
        Preferences.ServerBaseUrl = url;
        Preferences.Save();
        AuthState.Clear();
        Api?.UpdateBaseUrl(url);
        Auth = new AuthService(Api!, Preferences, AuthState);
        Client = new ClientService(Api!);
    }
}
