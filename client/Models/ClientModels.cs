namespace TPCWorkflow.Client.Models;

public sealed class CaptchaInfo
{
    public string CaptchaId { get; set; } = "";
    public string Image { get; set; } = "";
}

public sealed class UserProfile
{
    public int Id { get; set; }
    public string Username { get; set; } = "";
    public string DisplayName { get; set; } = "";
    public bool IsSystemAdmin { get; set; }
    public bool IsSectorAdmin { get; set; }
    public bool CanDesignWorkflow { get; set; }
    public bool CanViewInstances { get; set; }
    public bool CanExportInstances { get; set; }
}

public sealed class BadgeSummary
{
    public int TodoCount { get; set; }
    public int ParticipatedPendingCount { get; set; }
    public int MineUnreadCount { get; set; }
}

public sealed class NavMenuItem
{
    public string Key { get; set; } = "";
    public string Path { get; set; } = "";
    public string Label { get; set; } = "";
}

public sealed class TaskListItem
{
    public int TaskId { get; set; }
    public int Id { get; set; }
    public string? DefinitionName { get; set; }
    public string? InitiatorName { get; set; }
    public string? NodeName { get; set; }
    public string? DisplayNo { get; set; }
    public string? TaskCreatedAt { get; set; }
    public bool CanQuickApprove { get; set; }
    public string? Summary { get; set; }
}

public sealed class BootstrapData
{
    public UserProfile? User { get; set; }
    public BadgeSummary? Badges { get; set; }
    public TodoPreview? TodoPreview { get; set; }
    public List<NavMenuItem> NavMenu { get; set; } = [];
    public BrandingInfo? Branding { get; set; }
}

public sealed class TodoPreview
{
    public List<TaskListItem> Items { get; set; } = [];
    public int Total { get; set; }
}

public sealed class BrandingInfo
{
    public string? AppName { get; set; }
    public string? CompanyName { get; set; }
    public string? CompanyLogoUrl { get; set; }
}

public sealed class DeviceTokenPayload
{
    public int DeviceId { get; set; }
    public string DeviceUid { get; set; } = "";
    public string AccessToken { get; set; } = "";
    public string RefreshToken { get; set; } = "";
}

public sealed class TodoListResponse
{
    public List<TaskListItem> Items { get; set; } = [];
    public int Total { get; set; }
}

public sealed class ClientVersionPayload
{
    public string Version { get; set; } = "";
    public string? ReleaseNotes { get; set; }
    public bool Mandatory { get; set; }
    public string? PublishedAt { get; set; }
    public ClientDownloadBundle? Downloads { get; set; }
}

public sealed class ClientDownloadBundle
{
    public bool Available { get; set; }
    public ClientPackageInfo? Setup { get; set; }
    public ClientPackageInfo? Zip { get; set; }
    public ClientPackageInfo? Exe { get; set; }
}

public sealed class ClientPackageInfo
{
    public bool Available { get; set; }
    public string? Filename { get; set; }
    public long SizeBytes { get; set; }
    public string? DownloadUrl { get; set; }
}
