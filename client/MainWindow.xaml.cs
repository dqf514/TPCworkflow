using System.Net;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using Microsoft.Web.WebView2.Core;
using TPCWorkflow.Client.Models;
using TPCWorkflow.Client.Services;

namespace TPCWorkflow.Client;

public partial class MainWindow : Window
{
    private static readonly HashSet<string> DesktopNavKeys = new(StringComparer.OrdinalIgnoreCase)
    {
        "dashboard", "apply", "leave-calendar", "my-instances", "tasks",
    };

    private readonly ApiClient _api;
    private readonly AuthService _auth;
    private readonly ClientService _client;
    private readonly AppPreferences _prefs;
    private readonly NotificationService _notifications;
    private readonly TrayIconService _tray = new();
    private SseListener? _sse;
    private BootstrapData? _bootstrap;
    private bool _webReady;
    private bool _webViewAuthHooked;
    private bool _suppressNavChange;
    private bool _forceClose;
    private bool _initialNavDone;
    private string? _lastEmbedPath;
    private int _todoCount;
    private List<TaskListItem> _latestTodos = [];

    public void ForceClose() => _forceClose = true;

    public MainWindow(
        ApiClient api,
        AuthService auth,
        ClientService client,
        AppPreferences prefs,
        NotificationService notifications)
    {
        InitializeComponent();
        AppIconHelper.ApplyWindowIcon(this);
        WindowWorkAreaChrome.Attach(this);
        _api = api;
        _auth = auth;
        _client = client;
        _prefs = prefs;
        _notifications = notifications;

        _tray.Attach(this, RefreshAllAsync, () =>
        {
            _forceClose = true;
            ((App)System.Windows.Application.Current).RequestFullExit();
        });
        _notifications.BindTray(_tray, _prefs.EnableNotifications);

        Loaded += async (_, _) =>
        {
            try
            {
                await EnsureWebViewAsync();
                await RefreshAllAsync();
                await NavigateToDashboardAsync();
                StartSse();
                _ = MaybeCheckUpdateAsync();
            }
            catch (Exception ex)
            {
                System.Windows.MessageBox.Show(
                    this,
                    $"主界面初始化失败：{ex.Message}\n\n详情区可能无法加载网页，请检查网络与服务器配置。",
                    "提示",
                    MessageBoxButton.OK,
                    MessageBoxImage.Warning);
            }
        };
        Closing += OnClosing;
        StateChanged += (_, _) => UpdateMaximizeButtonIcon();
        Closed += (_, _) =>
        {
            _sse?.Dispose();
            _tray.Dispose();
        };
    }

    public void NavigateToPath(string path)
    {
        _initialNavDone = true;
        Dispatcher.InvokeAsync(async () => await NavigateWebAsync(path));
    }

    private void BrandHeader_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
    {
        if (e.ClickCount == 2)
        {
            ToggleMaximize();
            return;
        }
        if (e.ButtonState == MouseButtonState.Pressed)
            DragMove();
    }

    private void MinimizeButton_Click(object sender, RoutedEventArgs e) => WindowState = WindowState.Minimized;

    private void MaximizeButton_Click(object sender, RoutedEventArgs e) => ToggleMaximize();

    private void CloseButton_Click(object sender, RoutedEventArgs e) => Close();

    private void ToggleMaximize()
    {
        WindowState = WindowState == WindowState.Maximized ? WindowState.Normal : WindowState.Maximized;
        UpdateMaximizeButtonIcon();
    }

    private void UpdateMaximizeButtonIcon()
    {
        if (MaximizeButton is null)
            return;
        // Segoe MDL2: Maximize / Restore
        MaximizeButton.Content = WindowState == WindowState.Maximized ? "\uE923" : "\uE922";
    }

    private void OnClosing(object? sender, System.ComponentModel.CancelEventArgs e)
    {
        if (_forceClose)
            return;
        if (_prefs.MinimizeToTray)
        {
            e.Cancel = true;
            Hide();
            _tray.ShowBalloon("TPC 工作台", "程序已最小化到托盘，双击图标可恢复");
        }
    }

    private async Task EnsureWebViewAsync()
    {
        if (_webReady)
            return;
        await DetailWebView.EnsureCoreWebView2Async();
        var core = DetailWebView.CoreWebView2;

        if (!_webViewAuthHooked)
        {
            _webViewAuthHooked = true;
            var apiFilter = $"{_api.BaseUrl}/api/*";
            core.AddWebResourceRequestedFilter(apiFilter, CoreWebView2WebResourceContext.All);
            core.WebResourceRequested += OnWebResourceRequested;
            core.NavigationStarting += OnNavigationStarting;
            core.WebMessageReceived += (_, args) =>
            {
                try
                {
                    using var doc = JsonDocument.Parse(args.WebMessageAsJson);
                    HandleWebMessage(doc.RootElement);
                }
                catch
                {
                    /* ignore */
                }
            };
        }

        _webReady = true;
        await SyncCookiesToWebViewAsync();
    }

    private void OnWebResourceRequested(object? sender, CoreWebView2WebResourceRequestedEventArgs e)
    {
        if (!e.Request.Uri.Contains("/api/v1/", StringComparison.OrdinalIgnoreCase))
            return;

        var token = _auth.State.AccessToken;
        if (string.IsNullOrWhiteSpace(token))
            return;

        e.Request.Headers.SetHeader("Authorization", "Bearer " + token);
        e.Request.Headers.SetHeader("X-TPC-Client", "desktop");
    }

    private async void OnNavigationStarting(object? sender, CoreWebView2NavigationStartingEventArgs e)
    {
        try
        {
            var uri = new Uri(e.Uri);
            if (!uri.AbsolutePath.StartsWith("/login", StringComparison.OrdinalIgnoreCase))
                return;

            e.Cancel = true;
            if (await _auth.TryRefreshAsync().ConfigureAwait(true))
            {
                StartSse();
                await SyncCookiesToWebViewAsync();
                await NavigateWebAsync(_lastEmbedPath ?? "/tasks");
                return;
            }

            await ReloginAsync();
        }
        catch
        {
            /* ignore */
        }
    }

    private void HandleWebMessage(JsonElement root)
    {
        if (!root.TryGetProperty("type", out var typeProp))
            return;
        var type = typeProp.GetString() ?? "";
        Dispatcher.InvokeAsync(async () =>
        {
            switch (type)
            {
                case "task_completed":
                case "refresh_badges":
                    await RefreshAllAsync();
                    break;
                case "navigate":
                    if (root.TryGetProperty("path", out var pathProp))
                        await NavigateWebAsync(pathProp.GetString() ?? "/tasks");
                    break;
                case "workflow_submitted":
                    await RefreshAllAsync();
                    if (root.TryGetProperty("uuid", out var uuidProp))
                        await NavigateWebAsync("/instances/" + uuidProp.GetString());
                    break;
            }
        });
    }

    private async Task SyncCookiesToWebViewAsync()
    {
        if (!_webReady)
            return;
        var uri = new Uri(_api.BaseUrl);
        var manager = DetailWebView.CoreWebView2.CookieManager;
        foreach (Cookie cookie in _api.Cookies.GetCookies(uri))
        {
            var domain = string.IsNullOrWhiteSpace(cookie.Domain) ? uri.Host : cookie.Domain.TrimStart('.');
            var webCookie = manager.CreateCookie(cookie.Name, cookie.Value, cookie.Path, domain);
            webCookie.IsHttpOnly = cookie.HttpOnly;
            webCookie.IsSecure = cookie.Secure;
            if (cookie.Expires != DateTime.MinValue)
                webCookie.Expires = cookie.Expires;
            manager.AddOrUpdateCookie(webCookie);
        }
        await Task.CompletedTask;
    }

    private void StartSse()
    {
        _sse?.Dispose();
        if (string.IsNullOrWhiteSpace(_auth.State.AccessToken))
            return;
        _sse = new SseListener(_api.BaseUrl, _auth.State.AccessToken!);
        _sse.EventReceived += OnSseEvent;
        _sse.Start();
    }

    private void OnSseEvent(string eventType, JsonElement data)
    {
        Dispatcher.InvokeAsync(async () =>
        {
            if (eventType == "task.assigned" && data.TryGetProperty("task", out var taskNode))
            {
                var task = JsonSerializer.Deserialize<TaskListItem>(taskNode.GetRawText(), new JsonSerializerOptions
                {
                    PropertyNameCaseInsensitive = true,
                    PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
                });
                if (task is not null)
                {
                    _notifications.ShowNewTask(task);
                    _tray.ShowBalloon("新待办", $"{task.DefinitionName} · {task.InitiatorName}");
                }
            }
            await RefreshAllAsync();
        });
    }

    public async Task RefreshAllAsync()
    {
        await LoadBootstrapMetaAsync();
        await RefreshTodoDataAsync();
    }

    private async Task LoadBootstrapMetaAsync()
    {
        var res = await _client.LoadBootstrapAsync();
        if (!res.Ok || res.Data is null)
        {
            if (res.Code == "unauthorized" && await _auth.TryRefreshAsync())
            {
                StartSse();
                res = await _client.LoadBootstrapAsync();
            }
            if (!res.Ok || res.Data is null)
                return;
        }

        _bootstrap = res.Data;
        Title = _bootstrap.Branding?.AppName ?? "TPC 工作台";
        AppTitleText.Text = Title;
        UserNameText.Text = _bootstrap.User?.DisplayName ?? "";
        _todoCount = _bootstrap.Badges?.TodoCount ?? 0;
        UpdateTodoBadge(_todoCount);
        BuildNavMenu(_bootstrap.NavMenu);
    }

    private void BuildNavMenu(IReadOnlyList<NavMenuItem> items)
    {
        string? selectedPath = null;
        if (NavList.SelectedItem is ListBoxItem selected && selected.Tag is NavMenuItem nav)
            selectedPath = nav.Path;

        _suppressNavChange = true;
        NavList.Items.Clear();
        ListBoxItem? match = null;
        foreach (var item in items.Where(IsDesktopNavItem))
        {
            var listItem = CreateNavListItem(item);
            NavList.Items.Add(listItem);
            if (selectedPath is not null && item.Path == selectedPath)
                match = listItem;
        }
        if (match is not null)
            NavList.SelectedItem = match;
        else if (!_initialNavDone && NavList.Items.Count > 0)
        {
            ListBoxItem? dashboardItem = null;
            foreach (ListBoxItem item in NavList.Items)
            {
                if (item.Tag is NavMenuItem menuItem && menuItem.Key == "dashboard")
                {
                    dashboardItem = item;
                    break;
                }
            }
            NavList.SelectedItem = dashboardItem ?? NavList.Items[0];
        }
        _suppressNavChange = false;
    }

    private async Task NavigateToDashboardAsync()
    {
        if (_initialNavDone)
            return;
        _initialNavDone = true;

        var path = "/";
        if (_bootstrap?.NavMenu is not null)
        {
            var dashboard = _bootstrap.NavMenu.FirstOrDefault(n =>
                string.Equals(n.Key, "dashboard", StringComparison.OrdinalIgnoreCase));
            if (dashboard is not null && !string.IsNullOrWhiteSpace(dashboard.Path))
                path = dashboard.Path;
        }

        _suppressNavChange = true;
        foreach (ListBoxItem item in NavList.Items)
        {
            if (item.Tag is NavMenuItem nav && string.Equals(nav.Key, "dashboard", StringComparison.OrdinalIgnoreCase))
            {
                NavList.SelectedItem = item;
                break;
            }
        }
        _suppressNavChange = false;

        await NavigateWebAsync(path);
    }

    private static bool IsDesktopNavItem(NavMenuItem item)
    {
        if (DesktopNavKeys.Contains(item.Key))
            return true;
        return !item.Path.StartsWith("/admin", StringComparison.OrdinalIgnoreCase)
               && !item.Key.StartsWith("admin", StringComparison.OrdinalIgnoreCase);
    }

    private ListBoxItem CreateNavListItem(NavMenuItem item)
    {
        var panel = new StackPanel { Orientation = System.Windows.Controls.Orientation.Horizontal };
        panel.Children.Add(new TextBlock
        {
            Text = item.Label,
            FontSize = 13,
            VerticalAlignment = VerticalAlignment.Center,
        });

        if (item.Key == "tasks" && _todoCount > 0)
        {
            panel.Children.Add(new Border
            {
                Background = new SolidColorBrush(System.Windows.Media.Color.FromRgb(0xD1, 0x34, 0x38)),
                CornerRadius = new CornerRadius(8),
                Padding = new Thickness(6, 1, 6, 1),
                Margin = new Thickness(8, 0, 0, 0),
                VerticalAlignment = VerticalAlignment.Center,
                Child = new TextBlock
                {
                    Text = _todoCount > 99 ? "99+" : _todoCount.ToString(),
                    Foreground = System.Windows.Media.Brushes.White,
                    FontSize = 11,
                    FontWeight = FontWeights.SemiBold,
                },
            });
        }

        return new ListBoxItem
        {
            Content = panel,
            Tag = item,
        };
    }

    private void UpdateTodoBadge(int count)
    {
        _todoCount = count;
        _tray.UpdateBadge(count);
        _tray.RebuildMenu(_latestTodos);
        if (_bootstrap?.NavMenu is not null)
            BuildNavMenu(_bootstrap.NavMenu);
    }

    private async Task RefreshTodoDataAsync()
    {
        var todoRes = await _client.LoadTodoAsync();
        if (todoRes.Ok && todoRes.Data is not null)
        {
            _latestTodos = todoRes.Data.Items;
            UpdateTodoBadge(todoRes.Data.Total);
        }
    }

    private async void NavList_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (_suppressNavChange)
            return;
        if (NavList.SelectedItem is ListBoxItem item && item.Tag is NavMenuItem nav)
            await NavigateWebAsync(nav.Path);
    }

    private async Task NavigateWebAsync(string path)
    {
        _lastEmbedPath = path.StartsWith('/') ? path : "/" + path;
        await EnsureWebViewAsync();
        await SyncCookiesToWebViewAsync();
        EmptyHint.Visibility = Visibility.Collapsed;
        DetailWebView.Visibility = Visibility.Visible;
        DetailWebView.Source = new Uri(_client.BuildEmbedUrl(_lastEmbedPath));
    }

    private async Task MaybeCheckUpdateAsync()
    {
        if (!_prefs.AutoCheckUpdates)
            return;

        var last = _prefs.LastUpdateCheckAt;
        if (last.HasValue && DateTime.Now - last.Value < TimeSpan.FromHours(6))
            return;

        _prefs.LastUpdateCheckAt = DateTime.Now;
        _prefs.Save();

        try
        {
            var updates = new UpdateService(_api);
            var result = await updates.CheckAsync().ConfigureAwait(true);
            if (!result.UpdateAvailable || result.Remote is null)
                return;
            if (string.Equals(_prefs.SkippedUpdateVersion, result.Remote.Version, StringComparison.OrdinalIgnoreCase))
                return;

            var dlg = new UpdateWindow(updates, _prefs, result.Remote) { Owner = this };
            dlg.ShowDialog();
        }
        catch
        {
            /* 更新检查失败不影响正常使用 */
        }
    }

    private async Task ReloginAsync()
    {
        _forceClose = true;
        _sse?.Dispose();
        _tray.Dispose();
        ((App)System.Windows.Application.Current).BeginReloginHandoff();
        await Task.CompletedTask;
    }

    private void SettingsButton_Click(object sender, RoutedEventArgs e)
    {
        var updates = new UpdateService(_api);
        var dlg = new SettingsWindow(_prefs, updates) { Owner = this };
        if (dlg.ShowDialog() != true)
            return;
        ((App)System.Windows.Application.Current).ReloadServicesAfterSettings(dlg.Result, dlg.ServerChanged);
    }

    private async void LogoutButton_Click(object sender, RoutedEventArgs e)
    {
        _forceClose = true;
        _sse?.Dispose();
        await _auth.LogoutAsync();
        _tray.Dispose();
        var app = (App)System.Windows.Application.Current;
        app.SavedLogin.AutoLogin = false;
        app.SavedLogin.Save();
        app.BeginReloginHandoff();
    }
}
