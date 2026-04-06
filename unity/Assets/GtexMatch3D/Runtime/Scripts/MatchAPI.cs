using System;
using System.Collections;
using UnityEngine;
using UnityEngine.Networking;

namespace Gtex.Match3D.Runtime
{
    public sealed class MatchAPI
    {
        private readonly Func<string> _baseUrlProvider;
        private readonly int _timeoutSeconds;

        public MatchAPI(Func<string> baseUrlProvider, int timeoutSeconds)
        {
            _baseUrlProvider = baseUrlProvider;
            _timeoutSeconds = Mathf.Max(1, timeoutSeconds);
        }

        public IEnumerator GetLiveMatch(
            string matchId,
            Action<MatchResponse> onSuccess,
            Action<string, long> onError)
        {
            string baseUrl = _baseUrlProvider != null ? _baseUrlProvider() : string.Empty;
            if (string.IsNullOrWhiteSpace(baseUrl))
            {
                onError?.Invoke("Base URL is not configured.", 0L);
                yield break;
            }

            if (string.IsNullOrWhiteSpace(matchId))
            {
                onError?.Invoke("Match ID is not configured.", 0L);
                yield break;
            }

            string url = BuildLiveUrl(baseUrl, matchId);
            using (UnityWebRequest request = UnityWebRequest.Get(url))
            {
                request.downloadHandler = new DownloadHandlerBuffer();
                request.timeout = _timeoutSeconds;
                request.SetRequestHeader("Accept", "application/json");

                yield return request.SendWebRequest();

                if (request.result != UnityWebRequest.Result.Success)
                {
                    onError?.Invoke(FormatError(request), request.responseCode);
                    yield break;
                }

                MatchResponse response = Deserialize(
                    request.downloadHandler != null ? request.downloadHandler.text : string.Empty);
                if (response == null || string.IsNullOrWhiteSpace(response.matchId))
                {
                    onError?.Invoke("Live match response was invalid.", request.responseCode);
                    yield break;
                }

                response.Normalize();
                onSuccess?.Invoke(response);
            }
        }

        public static string BuildLiveUrl(string baseUrl, string matchId)
        {
            return baseUrl.TrimEnd('/') + "/match/" + UnityWebRequest.EscapeURL(matchId) + "/live";
        }

        private static MatchResponse Deserialize(string json)
        {
            if (string.IsNullOrWhiteSpace(json))
            {
                return null;
            }

            try
            {
                return JsonUtility.FromJson<MatchResponse>(json);
            }
            catch (Exception exception)
            {
                Debug.LogError("Failed to parse live match response.\n" + exception);
                return null;
            }
        }

        private static string FormatError(UnityWebRequest request)
        {
            string statusLine = request.responseCode > 0
                ? "HTTP " + request.responseCode
                : "Transport error";
            string detail = string.IsNullOrWhiteSpace(request.error)
                ? "Request failed."
                : request.error;
            return statusLine + ": " + detail;
        }
    }
}
