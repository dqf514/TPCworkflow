using TPCWorkflow.Client.Models;

namespace TPCWorkflow.Client.Services;

public sealed class AuthService
{
    private readonly ApiClient _api;
    private AppPreferences _prefs;
    private readonly LocalAuthState _state;

    public AuthService(ApiClient api, AppPreferences prefs, LocalAuthState state)
    {
        _api = api;
        _prefs = prefs;
        _state = state;
        _api.SetAccessToken(_state.AccessToken);
    }

    public LocalAuthState State => _state;
    public bool IsLoggedIn => !string.IsNullOrWhiteSpace(_state.AccessToken);

    public void UpdatePreferences(AppPreferences prefs) => _prefs = prefs;

    public async Task<ApiResult<LoginMethodsInfo>> LoadLoginMethodsAsync(CancellationToken ct = default)
    {
        return await _api.GetAsync<LoginMethodsInfo>("auth/login-methods", ct).ConfigureAwait(false);
    }

    public async Task<ApiResult<CaptchaInfo>> LoadCaptchaAsync(CancellationToken ct = default)
    {
        return await _api.GetAsync<CaptchaInfo>("auth/captcha", ct).ConfigureAwait(false);
    }

    public async Task<ApiResult<object?>> SendEmailCodeAsync(string email, CancellationToken ct = default)
    {
        return await _api.PostAsync<object?>("auth/email-code/send", new { email }, ct).ConfigureAwait(false);
    }

    public async Task<ApiResult<UserProfile>> LoginAsync(
        string username,
        string password,
        string captchaId,
        string captchaCode,
        CancellationToken ct = default)
    {
        var login = await _api.PostAsync<UserProfile>("auth/login", new
        {
            mode = "password",
            username,
            identifier = username,
            password,
            remember = true,
            captcha_id = captchaId,
            captcha_code = captchaCode,
        }, ct).ConfigureAwait(false);

        if (!login.Ok || login.Data is null)
            return login;

        return await RegisterDeviceAsync(login).ConfigureAwait(false);
    }

    public async Task<ApiResult<UserProfile>> LoginEmailAsync(
        string email,
        string code,
        CancellationToken ct = default)
    {
        var login = await _api.PostAsync<UserProfile>("auth/login", new
        {
            mode = "email_code",
            email,
            code,
        }, ct).ConfigureAwait(false);

        if (!login.Ok || login.Data is null)
            return login;

        return await RegisterDeviceAsync(login).ConfigureAwait(false);
    }

    private async Task<ApiResult<UserProfile>> RegisterDeviceAsync(ApiResult<UserProfile> login)
    {
        var device = await _api.PostAsync<DeviceTokenPayload>("auth/device/register", new
        {
            device_uid = _state.DeviceUid,
            device_name = _prefs.DeviceName,
        }).ConfigureAwait(false);

        if (!device.Ok || device.Data is null)
            return ApiResult<UserProfile>.Fail(device.Message);

        _state.AccessToken = device.Data.AccessToken;
        _state.RefreshToken = device.Data.RefreshToken;
        _state.ServerBaseUrl = _api.BaseUrl;
        _state.DisplayName = login.Data!.DisplayName;
        _state.Save();
        _api.SetAccessToken(_state.AccessToken);
        return login;
    }

    public async Task<bool> TryRefreshAsync(CancellationToken ct = default)
    {
        if (string.IsNullOrWhiteSpace(_state.RefreshToken))
            return false;

        var res = await _api.PostAsync<DeviceTokenPayload>("auth/device/refresh", new
        {
            device_uid = _state.DeviceUid,
            refresh_token = _state.RefreshToken,
        }, ct).ConfigureAwait(false);

        if (!res.Ok || res.Data is null)
            return false;

        _state.AccessToken = res.Data.AccessToken;
        _state.RefreshToken = res.Data.RefreshToken;
        _state.Save();
        _api.SetAccessToken(_state.AccessToken);
        return true;
    }

    public async Task LogoutAsync(CancellationToken ct = default)
    {
        try
        {
            await _api.PostAsync<object?>("auth/logout", null, ct).ConfigureAwait(false);
        }
        catch
        {
            /* ignore */
        }
        _state.Clear();
        _api.SetAccessToken(null);
    }
}
