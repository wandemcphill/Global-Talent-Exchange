using System;
using System.Collections;
using System.Text;
using UnityEngine;
using UnityEngine.Networking;

namespace FStudio.GTEX {
    public sealed class MatchAPI {
        private readonly Func<string> baseUrlProvider;
        private readonly Func<string> accessTokenProvider;
        private readonly Func<string> refreshTokenProvider;
        private readonly int timeoutSeconds;

        [Serializable]
        private sealed class RefreshRequestPayload {
            public string refresh_token;
        }

        public MatchAPI(
            Func<string> baseUrlProvider,
            Func<string> accessTokenProvider,
            Func<string> refreshTokenProvider,
            int timeoutSeconds) {
            this.baseUrlProvider = baseUrlProvider;
            this.accessTokenProvider = accessTokenProvider;
            this.refreshTokenProvider = refreshTokenProvider;
            this.timeoutSeconds = Mathf.Max(1, timeoutSeconds);
        }

        public IEnumerator GetLiveMatch(
            string matchId,
            Action<MatchResponse> onSuccess,
            Action<string, long> onError) {

            var baseUrl = baseUrlProvider != null ? baseUrlProvider() : string.Empty;
            if (string.IsNullOrWhiteSpace(baseUrl)) {
                onError?.Invoke("Base URL is not configured.", 0);
                yield break;
            }

            if (string.IsNullOrWhiteSpace(matchId)) {
                onError?.Invoke("Match ID is not configured.", 0);
                yield break;
            }

            var url = BuildLiveUrl(baseUrl, matchId);
            using (var request = UnityWebRequest.Get(url)) {
                request.downloadHandler = new DownloadHandlerBuffer();
                request.timeout = timeoutSeconds;
                request.SetRequestHeader("Accept", "application/json");
                var accessToken = accessTokenProvider != null ? accessTokenProvider() : string.Empty;
                if (!string.IsNullOrWhiteSpace(accessToken)) {
                    request.SetRequestHeader("Authorization", "Bearer " + accessToken.Trim());
                }

                yield return request.SendWebRequest();

                if (request.result != UnityWebRequest.Result.Success) {
                    onError?.Invoke(FormatError(request), request.responseCode);
                    yield break;
                }

                var response = Deserialize(request.downloadHandler != null ? request.downloadHandler.text : string.Empty);
                if (response == null || string.IsNullOrWhiteSpace(response.matchId)) {
                    onError?.Invoke("Live match response was invalid.", request.responseCode);
                    yield break;
                }

                response.Normalize();
                onSuccess?.Invoke(response);
            }
        }

        public IEnumerator RefreshLiveAccess(
            string matchId,
            Action<GtexLiveAccessGrant> onSuccess,
            Action<string, long> onError) {

            var baseUrl = baseUrlProvider != null ? baseUrlProvider() : string.Empty;
            if (string.IsNullOrWhiteSpace(baseUrl)) {
                onError?.Invoke("Base URL is not configured.", 0);
                yield break;
            }

            if (string.IsNullOrWhiteSpace(matchId)) {
                onError?.Invoke("Match ID is not configured.", 0);
                yield break;
            }

            var refreshToken = refreshTokenProvider != null ? refreshTokenProvider() : string.Empty;
            if (string.IsNullOrWhiteSpace(refreshToken)) {
                onError?.Invoke("Live refresh token is not configured.", 0);
                yield break;
            }

            var url = BuildLiveAccessRefreshUrl(baseUrl, matchId);
            var body = JsonUtility.ToJson(new RefreshRequestPayload { refresh_token = refreshToken.Trim() });
            using (var request = new UnityWebRequest(url, UnityWebRequest.kHttpVerbPOST)) {
                request.downloadHandler = new DownloadHandlerBuffer();
                request.uploadHandler = new UploadHandlerRaw(Encoding.UTF8.GetBytes(body));
                request.timeout = timeoutSeconds;
                request.SetRequestHeader("Accept", "application/json");
                request.SetRequestHeader("Content-Type", "application/json");

                yield return request.SendWebRequest();

                if (request.result != UnityWebRequest.Result.Success) {
                    onError?.Invoke(FormatError(request), request.responseCode);
                    yield break;
                }

                var grant = DeserializeLiveAccessGrant(request.downloadHandler != null ? request.downloadHandler.text : string.Empty);
                if (grant == null || !grant.HasAccessToken) {
                    onError?.Invoke("Live access refresh response was invalid.", request.responseCode);
                    yield break;
                }

                onSuccess?.Invoke(grant);
            }
        }

        public static string BuildLiveUrl(string baseUrl, string matchId) {
            return baseUrl.TrimEnd('/') + "/match/" + UnityWebRequest.EscapeURL(matchId) + "/live";
        }

        public static string BuildLiveAccessRefreshUrl(string baseUrl, string matchId) {
            return baseUrl.TrimEnd('/') + "/match/" + UnityWebRequest.EscapeURL(matchId) + "/unity-access/refresh";
        }

        private static MatchResponse Deserialize(string json) {
            if (string.IsNullOrWhiteSpace(json)) {
                return null;
            }

            try {
                return JsonUtility.FromJson<MatchResponse>(json);
            } catch (Exception exception) {
                Debug.LogError("[GTEX] Failed to parse live match response.\n" + exception);
                return null;
            }
        }

        private static GtexLiveAccessGrant DeserializeLiveAccessGrant(string json) {
            if (string.IsNullOrWhiteSpace(json)) {
                return null;
            }

            try {
                return JsonUtility.FromJson<GtexLiveAccessGrant>(json);
            } catch (Exception exception) {
                Debug.LogError("[GTEX] Failed to parse live access refresh response.\n" + exception);
                return null;
            }
        }

        private static string FormatError(UnityWebRequest request) {
            var statusLine = request.responseCode > 0 ? "HTTP " + request.responseCode : "Transport error";
            var detail = string.IsNullOrWhiteSpace(request.error) ? "Request failed." : request.error;
            return statusLine + ": " + detail;
        }
    }
}
