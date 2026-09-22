using System.IO;
using System.Text.Json;

namespace TPCWorkflow.Client.Services;

public sealed class AppPreferences
{
    public string ServerBaseUrl { get; set; } = "https://wf.imcsh.com";
    public string DeviceName { get; set; } = "Windows 工作台";
    public bool MinimizeToTray { get; set; } = true;
    public bool AutoStart { get; set; }
    public bool EnableNotifications { get; set; } = true;
    public bool EnableSound { get; set; }
    public bool AutoCheckUpdates { get; set; } = true;
    public string? SkippedUpdateVersion { get; set; }
    public DateTime? LastUpdateCheckAt { get; set; }

    private static string FilePath => Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
        "TPCWorkflow",
        "preferences.json");

    public static AppPreferences Load()
    {
        try
        {
            if (File.Exists(FilePath))
            {
                var json = File.ReadAllText(FilePath);
                var saved = JsonSerializer.Deserialize<AppPreferences>(json, JsonOpts());
                if (saved is not null)
                    return MergeWithDefaults(saved);
            }
        }
        catch
        {
            /* ignore */
        }

        return MergeWithDefaults(AppSettings.Load());
    }

    public void Save()
    {
        var dir = Path.GetDirectoryName(FilePath)!;
        Directory.CreateDirectory(dir);
        var json = JsonSerializer.Serialize(this, JsonOpts(indented: true));
        File.WriteAllText(FilePath, json);
    }

    private static AppPreferences MergeWithDefaults(AppPreferences source)
    {
        var defaults = AppSettings.Load();
        return new AppPreferences
        {
            ServerBaseUrl = string.IsNullOrWhiteSpace(source.ServerBaseUrl)
                ? defaults.ServerBaseUrl
                : source.ServerBaseUrl.TrimEnd('/'),
            DeviceName = string.IsNullOrWhiteSpace(source.DeviceName)
                ? defaults.DeviceName
                : source.DeviceName,
            MinimizeToTray = source.MinimizeToTray,
            AutoStart = source.AutoStart,
            EnableNotifications = source.EnableNotifications,
            EnableSound = source.EnableSound,
            AutoCheckUpdates = source.AutoCheckUpdates,
            SkippedUpdateVersion = source.SkippedUpdateVersion,
            LastUpdateCheckAt = source.LastUpdateCheckAt,
        };
    }

    private static AppPreferences MergeWithDefaults(AppSettings defaults) => new()
    {
        ServerBaseUrl = defaults.ServerBaseUrl.TrimEnd('/'),
        DeviceName = defaults.DeviceName,
        MinimizeToTray = defaults.MinimizeToTray,
        AutoStart = defaults.AutoStart,
        EnableNotifications = defaults.EnableNotifications,
        EnableSound = defaults.EnableSound,
        AutoCheckUpdates = true,
    };

    private static JsonSerializerOptions JsonOpts(bool indented = false) => new()
    {
        PropertyNameCaseInsensitive = true,
        WriteIndented = indented,
    };
}

public sealed class AppSettings
{
    public string ServerBaseUrl { get; set; } = "https://wf.imcsh.com";
    public string DeviceName { get; set; } = "Windows 工作台";
    public bool MinimizeToTray { get; set; } = true;
    public bool AutoStart { get; set; }
    public bool EnableNotifications { get; set; } = true;
    public bool EnableSound { get; set; }

    public static AppSettings Load()
    {
        var path = Path.Combine(AppContext.BaseDirectory, "appsettings.json");
        if (!File.Exists(path))
            return new AppSettings();
        var json = File.ReadAllText(path);
        return JsonSerializer.Deserialize<AppSettings>(json, new JsonSerializerOptions
        {
            PropertyNameCaseInsensitive = true,
        }) ?? new AppSettings();
    }
}

public sealed class LocalAuthState
{
    public string DeviceUid { get; set; } = Guid.NewGuid().ToString("N");
    public string? AccessToken { get; set; }
    public string? RefreshToken { get; set; }
    public string? ServerBaseUrl { get; set; }
    public string? DisplayName { get; set; }

    private static string StorePath => Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
        "TPCWorkflow",
        "auth.json");

    public static LocalAuthState Load()
    {
        try
        {
            if (!File.Exists(StorePath))
                return new LocalAuthState();
            var json = File.ReadAllText(StorePath);
            return JsonSerializer.Deserialize<LocalAuthState>(json, new JsonSerializerOptions
            {
                PropertyNameCaseInsensitive = true,
            }) ?? new LocalAuthState();
        }
        catch
        {
            return new LocalAuthState();
        }
    }

    public void Save()
    {
        var dir = Path.GetDirectoryName(StorePath)!;
        Directory.CreateDirectory(dir);
        var json = JsonSerializer.Serialize(this, new JsonSerializerOptions { WriteIndented = true });
        File.WriteAllText(StorePath, json);
    }

    public void Clear()
    {
        AccessToken = null;
        RefreshToken = null;
        DisplayName = null;
        Save();
    }
}

public static class PendingNavigation
{
    private static string FilePath => Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
        "TPCWorkflow",
        "pending-nav.txt");

    public static void Write(string path)
    {
        var dir = Path.GetDirectoryName(FilePath)!;
        Directory.CreateDirectory(dir);
        File.WriteAllText(FilePath, path.Trim());
    }

    public static string? ReadAndClear()
    {
        try
        {
            if (!File.Exists(FilePath))
                return null;
            var text = File.ReadAllText(FilePath).Trim();
            File.Delete(FilePath);
            return string.IsNullOrWhiteSpace(text) ? null : text;
        }
        catch
        {
            return null;
        }
    }
}
