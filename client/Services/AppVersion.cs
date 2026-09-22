using System.Reflection;

namespace TPCWorkflow.Client.Services;

public static class AppVersion
{
    public static string Current
    {
        get
        {
            var v = Assembly.GetExecutingAssembly().GetName().Version;
            if (v is null)
                return "0.0.0";
            return $"{v.Major}.{v.Minor}.{v.Build}";
        }
    }

    public static bool TryParse(string? text, out Version version)
    {
        version = new Version(0, 0, 0);
        if (string.IsNullOrWhiteSpace(text))
            return false;
        text = text.Trim();
        if (Version.TryParse(text, out var parsed) && parsed is not null)
        {
            version = parsed;
            return true;
        }
        var parts = text.Split('.', StringSplitOptions.RemoveEmptyEntries);
        if (parts.Length == 0)
            return false;
        var nums = new int[Math.Min(4, parts.Length)];
        for (var i = 0; i < nums.Length; i++)
        {
            if (!int.TryParse(parts[i], out nums[i]))
                return false;
        }
        version = nums.Length switch
        {
            1 => new Version(nums[0], 0),
            2 => new Version(nums[0], nums[1]),
            3 => new Version(nums[0], nums[1], nums[2]),
            _ => new Version(nums[0], nums[1], nums[2], nums[3]),
        };
        return true;
    }

    public static bool IsRemoteNewer(string? remoteVersion)
    {
        if (!TryParse(Current, out var local) || !TryParse(remoteVersion, out var remote))
            return false;
        return remote > local;
    }
}
