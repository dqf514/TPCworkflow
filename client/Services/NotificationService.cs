using TPCWorkflow.Client.Models;

namespace TPCWorkflow.Client.Services;

public sealed class NotificationService
{
    private TrayIconService? _tray;
    private bool _enabled = true;

    public void BindTray(TrayIconService tray, bool enabled)
    {
        _tray = tray;
        _enabled = enabled;
    }

    public void SetEnabled(bool enabled) => _enabled = enabled;

    public void ShowNewTask(TaskListItem task)
    {
        if (!_enabled || _tray is null)
            return;
        var title = task.DefinitionName ?? "新待办";
        var body = $"{task.InitiatorName ?? "未知"} · {task.NodeName ?? task.DisplayNo ?? "待处理"}";
        _tray.ShowBalloon("新待办：" + title, body);
    }

    public void ShowMessage(string title, string body)
    {
        if (!_enabled || _tray is null)
            return;
        _tray.ShowBalloon(title, body);
    }
}
