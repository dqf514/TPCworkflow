using System.IO;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace TPCWorkflow.Client.Services;

public sealed class SavedLoginCredentials
{
    public string? Username { get; set; }
    public string? Email { get; set; }
    public bool RememberUsername { get; set; } = true;
    public bool RememberEmail { get; set; } = true;
    public bool RememberPassword { get; set; }
    public bool AutoLogin { get; set; } = true;
    public string? ProtectedPassword { get; set; }

    private static string FilePath => Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
        "TPCWorkflow",
        "saved-login.json");

    public static SavedLoginCredentials Load()
    {
        try
        {
            if (!File.Exists(FilePath))
                return new SavedLoginCredentials();
            var json = File.ReadAllText(FilePath);
            return JsonSerializer.Deserialize<SavedLoginCredentials>(json, new JsonSerializerOptions
            {
                PropertyNameCaseInsensitive = true,
            }) ?? new SavedLoginCredentials();
        }
        catch
        {
            return new SavedLoginCredentials();
        }
    }

    public void Save()
    {
        var dir = Path.GetDirectoryName(FilePath)!;
        Directory.CreateDirectory(dir);
        var json = JsonSerializer.Serialize(this, new JsonSerializerOptions { WriteIndented = true });
        File.WriteAllText(FilePath, json);
    }

    public void SetPassword(string? plain)
    {
        if (string.IsNullOrEmpty(plain))
        {
            ProtectedPassword = null;
            return;
        }
        var bytes = Encoding.UTF8.GetBytes(plain);
        var protectedBytes = ProtectedData.Protect(bytes, null, DataProtectionScope.CurrentUser);
        ProtectedPassword = Convert.ToBase64String(protectedBytes);
    }

    public string? GetPassword()
    {
        if (string.IsNullOrWhiteSpace(ProtectedPassword))
            return null;
        try
        {
            var protectedBytes = Convert.FromBase64String(ProtectedPassword);
            var bytes = ProtectedData.Unprotect(protectedBytes, null, DataProtectionScope.CurrentUser);
            return Encoding.UTF8.GetString(bytes);
        }
        catch
        {
            return null;
        }
    }

    public void ClearPassword()
    {
        ProtectedPassword = null;
        RememberPassword = false;
    }
}
