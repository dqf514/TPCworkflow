using System.IO;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text.Json;
using TPCWorkflow.Client.Models;

namespace TPCWorkflow.Client.Services;

public sealed class ClientService
{
    private readonly ApiClient _api;

    public ClientService(ApiClient api)
    {
        _api = api;
    }

    public async Task<ApiResult<BootstrapData>> LoadBootstrapAsync(CancellationToken ct = default)
    {
        return await _api.GetAsync<BootstrapData>("client/bootstrap", ct).ConfigureAwait(false);
    }

    public async Task<ApiResult<TodoListResponse>> LoadTodoAsync(string? keyword = null, CancellationToken ct = default)
    {
        var path = "workflow/tasks/todo?page=1&page_size=50";
        if (!string.IsNullOrWhiteSpace(keyword))
            path += "&keyword=" + Uri.EscapeDataString(keyword);
        return await _api.GetAsync<TodoListResponse>(path, ct).ConfigureAwait(false);
    }

    public async Task<ApiResult<TodoListResponse>> LoadDoneAsync(string? keyword = null, CancellationToken ct = default)
    {
        var path = "workflow/tasks/done?page=1&page_size=50";
        if (!string.IsNullOrWhiteSpace(keyword))
            path += "&keyword=" + Uri.EscapeDataString(keyword);
        return await _api.GetAsync<TodoListResponse>(path, ct).ConfigureAwait(false);
    }

    public async Task<ApiResult<object?>> QuickApproveAsync(int taskId, CancellationToken ct = default)
    {
        return await _api.PostAsync<object?>("workflow/tasks/batch-complete", new
        {
            task_ids = new[] { taskId },
            action = "approve",
            comment = "同意",
        }, ct).ConfigureAwait(false);
    }

    public string BuildEmbedUrl(string path)
    {
        var p = path.StartsWith('/') ? path : "/" + path;
        if (p.Contains('?'))
            return _api.BaseUrl + p + "&embed=desktop";
        return _api.BaseUrl + p + "?embed=desktop";
    }
}

public sealed class SseListener : IDisposable
{
    private readonly HttpClient _http;
    private CancellationTokenSource? _cts;
    private Task? _loop;

    public event Action<string, JsonElement>? EventReceived;
    public event Action? ConnectionLost;

    public SseListener(string baseUrl, string accessToken)
    {
        _http = new HttpClient
        {
            BaseAddress = new Uri(baseUrl.TrimEnd('/') + "/"),
            Timeout = Timeout.InfiniteTimeSpan,
        };
        _http.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", accessToken);
        _http.DefaultRequestHeaders.Accept.Add(new MediaTypeWithQualityHeaderValue("text/event-stream"));
    }

    public void Start()
    {
        Stop();
        _cts = new CancellationTokenSource();
        _loop = Task.Run(() => RunAsync(_cts.Token));
    }

    public void Stop()
    {
        _cts?.Cancel();
        try
        {
            _loop?.Wait(TimeSpan.FromSeconds(2));
        }
        catch
        {
            /* ignore */
        }
        _cts?.Dispose();
        _cts = null;
        _loop = null;
    }

    private async Task RunAsync(CancellationToken ct)
    {
        while (!ct.IsCancellationRequested)
        {
            try
            {
                using var req = new HttpRequestMessage(HttpMethod.Get, "api/v1/client/events/stream");
                using var res = await _http.SendAsync(req, HttpCompletionOption.ResponseHeadersRead, ct).ConfigureAwait(false);
                res.EnsureSuccessStatusCode();
                await using var stream = await res.Content.ReadAsStreamAsync(ct).ConfigureAwait(false);
                using var reader = new StreamReader(stream);
                string? eventName = null;
                while (!ct.IsCancellationRequested)
                {
                    var line = await reader.ReadLineAsync(ct).ConfigureAwait(false);
                    if (line is null)
                        break;
                    if (line.StartsWith("event:", StringComparison.Ordinal))
                    {
                        eventName = line["event:".Length..].Trim();
                        continue;
                    }
                    if (line.StartsWith("data:", StringComparison.Ordinal) && eventName is not null)
                    {
                        var json = line["data:".Length..].Trim();
                        try
                        {
                            using var doc = JsonDocument.Parse(json);
                            EventReceived?.Invoke(eventName, doc.RootElement.Clone());
                        }
                        catch
                        {
                            /* ignore malformed event */
                        }
                        eventName = null;
                    }
                }
            }
            catch (OperationCanceledException)
            {
                break;
            }
            catch
            {
                ConnectionLost?.Invoke();
                try
                {
                    await Task.Delay(5000, ct).ConfigureAwait(false);
                }
                catch
                {
                    break;
                }
            }
        }
    }

    public void Dispose()
    {
        Stop();
        _http.Dispose();
    }
}
