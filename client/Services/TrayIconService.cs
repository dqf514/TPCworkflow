using System.Drawing;
using System.Windows;
using System.Windows.Forms;
using TPCWorkflow.Client.Models;

namespace TPCWorkflow.Client.Services;

public sealed class TrayIconService : IDisposable
{
    private NotifyIcon? _icon;
    private Window? _host;
    private Func<Task>? _onRefresh;
    private Action? _onExit;

    public void Attach(Window host, Func<Task> onRefresh, Action onExit)
    {
        _host = host;
        _onRefresh = onRefresh;
        _onExit = onExit;
        _icon = new NotifyIcon
        {
            Icon = AppIconHelper.LoadTrayIcon(),
            Text = "TPC 工作台",
            Visible = true,
        };
        _icon.DoubleClick += (_, _) => ShowHost();
        RebuildMenu();
    }

    public void UpdateBadge(int count)
    {
        if (_icon is null)
            return;
        _icon.Text = count > 0 ? $"TPC 工作台（{count} 条待办）" : "TPC 工作台";
    }

    public void ShowBalloon(string title, string text)
    {
        _icon?.ShowBalloonTip(4000, title, text, ToolTipIcon.Info);
    }

    public void RebuildMenu(IReadOnlyList<TaskListItem>? quickTasks = null)
    {
        if (_icon is null)
            return;
        var menu = new ContextMenuStrip();
        menu.Items.Add("打开工作台", null, (_, _) => ShowHost());
        if (_onRefresh is not null)
            menu.Items.Add("刷新待办", null, async (_, _) => await _onRefresh());
        if (quickTasks is { Count: > 0 })
        {
            menu.Items.Add(new ToolStripSeparator());
            foreach (var task in quickTasks.Take(5))
            {
                var label = $"{task.DefinitionName} · {task.InitiatorName}";
                menu.Items.Add(label, null, (_, _) =>
                {
                    PendingNavigation.Write($"/tasks/{task.TaskId}");
                    ShowHost();
                });
            }
        }
        menu.Items.Add(new ToolStripSeparator());
        menu.Items.Add("退出", null, (_, _) => _onExit?.Invoke());
        _icon.ContextMenuStrip = menu;
    }

    public void ShowHost()
    {
        if (_host is null)
            return;
        _host.Show();
        _host.WindowState = WindowState.Normal;
        _host.Activate();
    }

    public void HideHost()
    {
        _host?.Hide();
    }

    private static Icon LoadIcon()
    {
        return AppIconHelper.LoadTrayIcon();
    }

    public void Dispose()
    {
        if (_icon is not null)
        {
            _icon.Visible = false;
            _icon.Dispose();
            _icon = null;
        }
    }
}
