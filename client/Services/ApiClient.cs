using System.IO;
using System.Net;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace TPCWorkflow.Client.Services;

public sealed class ApiClient
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNameCaseInsensitive = true,
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
    };

    private readonly HttpClient _http;
    private readonly CookieContainer _cookies = new();

    public ApiClient(string baseUrl)
    {
        BaseUrl = baseUrl.TrimEnd('/');
        var handler = new HttpClientHandler
        {
            CookieContainer = _cookies,
            UseCookies = true,
            AutomaticDecompression = DecompressionMethods.All,
        };
        _http = new HttpClient(handler)
        {
            BaseAddress = new Uri(BaseUrl + "/"),
            Timeout = TimeSpan.FromSeconds(60),
        };
        _http.DefaultRequestHeaders.Accept.Add(new MediaTypeWithQualityHeaderValue("application/json"));
        _http.DefaultRequestHeaders.Add("X-TPC-Client", "desktop");
    }

    public string BaseUrl { get; private set; }

    public CookieContainer Cookies => _cookies;

    public void SetAccessToken(string? token)
    {
        var value = string.IsNullOrWhiteSpace(token) ? null : token.Trim();
        _http.DefaultRequestHeaders.Authorization = value is null
            ? null
            : new AuthenticationHeaderValue("Bearer", value);
    }

    public void UpdateBaseUrl(string baseUrl)
    {
        BaseUrl = baseUrl.TrimEnd('/');
        _http.BaseAddress = new Uri(BaseUrl + "/");
    }

    public async Task<ApiResult<object?>> HealthCheckAsync(CancellationToken ct = default)
    {
        using var res = await _http.GetAsync("api/v1/health", ct).ConfigureAwait(false);
        return await ParseAsync<object?>(res, "api/v1/health").ConfigureAwait(false);
    }

    public async Task<ApiResult<T>> GetAsync<T>(string path, CancellationToken ct = default)
    {
        var full = $"api/v1/{path.TrimStart('/')}";
        using var res = await _http.GetAsync(full, ct).ConfigureAwait(false);
        return await ParseAsync<T>(res, full).ConfigureAwait(false);
    }

    public async Task<ApiResult<T>> PostAsync<T>(string path, object? body = null, CancellationToken ct = default)
    {
        var full = $"api/v1/{path.TrimStart('/')}";
        using var content = body is null
            ? null
            : new StringContent(JsonSerializer.Serialize(body, JsonOptions), Encoding.UTF8, "application/json");
        using var res = await _http.PostAsync(full, content, ct).ConfigureAwait(false);
        return await ParseAsync<T>(res, full).ConfigureAwait(false);
    }

    public async Task<ApiResult<T>> DeleteAsync<T>(string path, CancellationToken ct = default)
    {
        var full = $"api/v1/{path.TrimStart('/')}";
        using var res = await _http.DeleteAsync(full, ct).ConfigureAwait(false);
        return await ParseAsync<T>(res, full).ConfigureAwait(false);
    }

    public async Task DownloadToFileAsync(
        string absoluteUrl,
        string destinationPath,
        IProgress<double>? progress = null,
        CancellationToken ct = default)
    {
        using var req = new HttpRequestMessage(HttpMethod.Get, absoluteUrl);
        using var res = await _http.SendAsync(req, HttpCompletionOption.ResponseHeadersRead, ct).ConfigureAwait(false);
        if (!res.IsSuccessStatusCode)
            throw new IOException($"下载失败：HTTP {(int)res.StatusCode}");

        var total = res.Content.Headers.ContentLength ?? -1L;
        await using var input = await res.Content.ReadAsStreamAsync(ct).ConfigureAwait(false);
        await using var output = new FileStream(destinationPath, FileMode.Create, FileAccess.Write, FileShare.None);
        var buffer = new byte[1024 * 128];
        long readTotal = 0;
        int read;
        while ((read = await input.ReadAsync(buffer, ct).ConfigureAwait(false)) > 0)
        {
            await output.WriteAsync(buffer.AsMemory(0, read), ct).ConfigureAwait(false);
            readTotal += read;
            if (total > 0 && progress is not null)
                progress.Report(readTotal * 100d / total);
        }
        if (progress is not null)
            progress.Report(100);
    }

    private static async Task<ApiResult<T>> ParseAsync<T>(HttpResponseMessage res, string path)
    {
        var text = await res.Content.ReadAsStringAsync().ConfigureAwait(false);
        var trimmed = text.TrimStart();

        if (trimmed.StartsWith('<'))
        {
            return ApiResult<T>.Fail(
                $"无法访问接口 {path}：服务器返回了网页（HTML），不是 API 数据。\n" +
                "请检查：① 齿轮中的服务器地址是否正确；② Nginx 是否已将 /api/ 反代到后端。");
        }

        if (string.IsNullOrWhiteSpace(trimmed))
            return ApiResult<T>.Fail($"接口 {path} 返回为空（HTTP {(int)res.StatusCode}）");

        if (!res.IsSuccessStatusCode)
        {
            try
            {
                var err = JsonSerializer.Deserialize<ApiEnvelope<T>>(trimmed, JsonOptions);
                if (err is not null && !string.IsNullOrWhiteSpace(err.Message))
                    return ApiResult<T>.Fail(err.Message, err.Code);
            }
            catch
            {
                /* ignore */
            }
            return ApiResult<T>.Fail($"请求失败：HTTP {(int)res.StatusCode}");
        }

        try
        {
            var envelope = JsonSerializer.Deserialize<ApiEnvelope<T>>(trimmed, JsonOptions);
            if (envelope is null)
                return ApiResult<T>.Fail("响应解析失败");
            if (!envelope.Ok)
                return ApiResult<T>.Fail(envelope.Message ?? "请求失败", envelope.Code);
            return ApiResult<T>.Success(envelope.Data, envelope.Message);
        }
        catch (JsonException)
        {
            var preview = trimmed.Length > 80 ? trimmed[..80] + "…" : trimmed;
            return ApiResult<T>.Fail($"接口返回格式异常，非 JSON：{preview}");
        }
        catch (Exception ex)
        {
            return ApiResult<T>.Fail($"响应异常：{ex.Message}");
        }
    }
}

public sealed class ApiEnvelope<T>
{
    public bool Ok { get; set; }
    public string? Message { get; set; }
    public string? Code { get; set; }
    public T? Data { get; set; }
}

public sealed class ApiResult<T>
{
    public bool Ok { get; init; }
    public string Message { get; init; } = "";
    public string? Code { get; init; }
    public T? Data { get; init; }

    public static ApiResult<T> Success(T? data, string? message = null) => new()
    {
        Ok = true,
        Data = data,
        Message = message ?? "",
    };

    public static ApiResult<T> Fail(string message, string? code = null) => new()
    {
        Ok = false,
        Message = message,
        Code = code,
    };
}
