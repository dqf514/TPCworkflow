using System.Drawing;
using System.IO;
using System.Reflection;
using System.Windows;
using System.Windows.Media;
using System.Windows.Media.Imaging;

namespace TPCWorkflow.Client.Services;

/// <summary>
/// 统一窗口、任务栏与托盘图标来源。单文件发布时图标内嵌在程序集中，不依赖 exe 旁 Assets 目录。
/// </summary>
public static class AppIconHelper
{
    private static readonly object Gate = new();
    private static Icon? _cachedIcon;
    private static ImageSource? _cachedLogo;

    public static ImageSource? LogoImage
    {
        get
        {
            if (_cachedLogo is not null)
                return _cachedLogo;
            _cachedLogo = TryLoadLogoImage();
            return _cachedLogo;
        }
    }

    public static void ApplyWindowIcon(Window window)
    {
        try
        {
            var icon = LogoImage;
            if (icon is not null)
                window.Icon = icon;
        }
        catch
        {
            /* 窗口图标加载失败不影响启动 */
        }
    }

    public static Icon LoadTrayIcon()
    {
        lock (Gate)
        {
            if (_cachedIcon is not null)
                return (Icon)_cachedIcon.Clone();

            var icon = TryLoadTrayIcon();
            _cachedIcon = icon;
            return (Icon)icon.Clone();
        }
    }

    private static ImageSource? TryLoadLogoImage()
    {
        try
        {
            var packUri = new Uri("pack://application:,,,/Assets/app-icon.png", UriKind.Absolute);
            var image = new BitmapImage();
            image.BeginInit();
            image.UriSource = packUri;
            image.CacheOption = BitmapCacheOption.OnLoad;
            image.EndInit();
            image.Freeze();
            return image;
        }
        catch
        {
            /* fall through */
        }

        var stream = OpenFirstIconStream("app-icon.png");
        if (stream is null)
            return null;

        try
        {
            var image = new BitmapImage();
            image.BeginInit();
            image.StreamSource = stream;
            image.CacheOption = BitmapCacheOption.OnLoad;
            image.EndInit();
            image.Freeze();
            return image;
        }
        catch
        {
            return null;
        }
        finally
        {
            stream.Dispose();
        }
    }

    private static Icon TryLoadTrayIcon()
    {
        var stream = OpenFirstIconStream("app.ico");
        if (stream is not null)
        {
            using (stream)
                return new Icon(stream);
        }

        var exe = Environment.ProcessPath;
        if (!string.IsNullOrWhiteSpace(exe))
        {
            var extracted = Icon.ExtractAssociatedIcon(exe);
            if (extracted is not null)
                return extracted;
        }

        return SystemIcons.Application;
    }

    private static Stream? OpenFirstIconStream(string fileName)
    {
        var asm = Assembly.GetExecutingAssembly();
        var baseName = asm.GetName().Name ?? "TPCWorkflow.Client";
        foreach (var name in new[]
                 {
                     $"Assets.{fileName}",
                     $"{baseName}.Assets.{fileName}",
                     fileName,
                 })
        {
            var embedded = asm.GetManifestResourceStream(name);
            if (embedded is not null)
                return embedded;
        }

        var diskPath = Path.Combine(AppContext.BaseDirectory, "Assets", fileName);
        if (File.Exists(diskPath))
            return File.OpenRead(diskPath);

        return null;
    }
}
