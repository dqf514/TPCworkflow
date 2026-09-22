namespace TPCWorkflow.Client.Models;

public sealed class TaskRowViewModel
{
    public int TaskId { get; init; }
    public string Title { get; init; } = "";
    public string Subtitle { get; init; } = "";
    public bool CanQuickApprove { get; init; }
    public TaskListItem Source { get; init; } = new();
}
