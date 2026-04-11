#if UNITY_EDITOR
using System;
using System.Collections;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using Stopwatch = System.Diagnostics.Stopwatch;
using FStudio.GTEX.Core;
using FStudio.GTEX.Simulation;
using Shared.Responses;
using UnityEditor;
using UnityEngine;

namespace FStudio.GTEX.Editor
{
    public static class GtexLivePlaybackSmokeVerifier
    {
        private sealed class VerificationResult
        {
            public string RequestPath;
            public string Scoreline;
            public float MatchMinute;

            public string Summary =>
                "RequestPath=" + RequestPath +
                ", Score=" + Scoreline +
                ", Minute=" + MatchMinute.ToString("0.0") + ".";
        }

        [MenuItem("Tools/GTEX/Simulation/Verify Live Playback Smoke")]
        public static void VerifyFromEditorMenu()
        {
            Verify();
        }

        public static void VerifyFromCommandLine()
        {
            Verify();
        }

        private static void Verify()
        {
            const string actionName = "Live playback smoke test";
            var stopwatch = Stopwatch.StartNew();
            GtexRuntimeToolStatus.Begin(actionName);
            Debug.Log("[GTEX Live Smoke] Starting live playback smoke verification.");
            DestroyExistingRuntimeObjects();

            MockLiveMatchServer server = null;

            try
            {
                server = new MockLiveMatchServer(BuildSmokePayload("live-smoke-test"));

                var config = new GtexMatchConfig
                {
                    enabled = true,
                    autoStartOnBoot = true,
                    runtimeMode = "live",
                    matchId = "live-smoke-test",
                    environment = "custom",
                    customBaseUrl = server.BaseUrl,
                    liveAccessToken = "live-smoke-test-token",
                    timeoutSeconds = 3,
                    verboseLogging = false
                };

                config.EnsureDefaults();

                if (!GtexRuntimeBootstrap.TryAutoStart(config))
                {
                    throw new InvalidOperationException("Runtime bootstrap did not start live playback.");
                }

                var liveRuntime = UnityEngine.Object.FindFirstObjectByType<GtexMatchRuntime>();
                if (liveRuntime == null)
                {
                    throw new InvalidOperationException("Live GTEX runtime was not created.");
                }

                if (UnityEngine.Object.FindFirstObjectByType<GtexSimRuntimeHost>() != null)
                {
                    throw new InvalidOperationException("Local simulation host should not be created in live playback mode.");
                }

                var response = FetchLiveMatch(config, server.BaseUrl);

                if (server.RequestCount < 1)
                {
                    throw new InvalidOperationException("Smoke server did not receive a live match request.");
                }

                var expectedPath = "/match/" + config.matchId + "/live";
                if (!string.Equals(server.LastRequestPath, expectedPath, StringComparison.Ordinal))
                {
                    throw new InvalidOperationException(
                        "Smoke server received unexpected request path: " +
                        server.LastRequestPath +
                        " (expected " +
                        expectedPath +
                        ").");
                }

                if (!liveRuntime.TryConsumeLiveState(response))
                {
                    throw new InvalidOperationException("Live runtime did not accept the smoke response.");
                }

                if (!liveRuntime.HasReceivedLiveState)
                {
                    throw new InvalidOperationException("Live runtime did not cache the smoke response.");
                }

                if (Math.Abs(liveRuntime.LastKnownClockMinute - 12.5f) > 0.01f)
                {
                    throw new InvalidOperationException(
                        "Unexpected smoke minute: " + liveRuntime.LastKnownClockMinute.ToString("0.0") + ".");
                }

                if (liveRuntime.LastKnownHomeScore != 2 || liveRuntime.LastKnownAwayScore != 1)
                {
                    throw new InvalidOperationException(
                        "Unexpected smoke scoreline: " +
                        liveRuntime.LastKnownHomeScore +
                        "-" +
                        liveRuntime.LastKnownAwayScore +
                        ".");
                }

                if (!string.IsNullOrWhiteSpace(liveRuntime.LastTransportError))
                {
                    throw new InvalidOperationException("Live runtime reported a transport error during smoke verification.");
                }

                var result = new VerificationResult
                {
                    RequestPath = server.LastRequestPath,
                    Scoreline = liveRuntime.LastKnownHomeScore + "-" + liveRuntime.LastKnownAwayScore,
                    MatchMinute = liveRuntime.LastKnownClockMinute
                };

                stopwatch.Stop();
                GtexRuntimeToolStatus.CompleteSuccess(
                    actionName,
                    "Live playback smoke test passed. " + result.Summary,
                    result.Scoreline,
                    stopwatch.Elapsed.TotalMilliseconds);

                Debug.Log("[GTEX Live Smoke] Success. " + result.Summary);
            }
            catch (Exception exception)
            {
                stopwatch.Stop();
                GtexRuntimeToolStatus.CompleteFailure(actionName, exception, stopwatch.Elapsed.TotalMilliseconds);
                throw;
            }
            finally
            {
                server?.Dispose();
                DestroyExistingRuntimeObjects();
            }
        }

        private static MatchResponse FetchLiveMatch(GtexMatchConfig config, string baseUrl)
        {
            var requestUrl = MatchAPI.BuildLiveUrl(baseUrl, config.matchId);
            var request = (HttpWebRequest)WebRequest.Create(requestUrl);
            request.Method = "GET";
            request.Accept = "application/json";
            request.Timeout = Mathf.Max(1000, config.timeoutSeconds * 1000);
            request.ReadWriteTimeout = request.Timeout;
            if (!string.IsNullOrWhiteSpace(config.liveAccessToken))
            {
                request.Headers[HttpRequestHeader.Authorization] = "Bearer " + config.liveAccessToken.Trim();
            }

            try
            {
                using var response = (HttpWebResponse)request.GetResponse();
                using var stream = response.GetResponseStream();
                using var reader = new StreamReader(stream ?? Stream.Null, Encoding.UTF8, true, 1024, false);
                var json = reader.ReadToEnd();
                var matchResponse = JsonUtility.FromJson<MatchResponse>(json);
                if (matchResponse == null || string.IsNullOrWhiteSpace(matchResponse.matchId))
                {
                    throw new InvalidOperationException("Live smoke fetch returned an invalid response payload.");
                }

                matchResponse.Normalize();
                return matchResponse;
            }
            catch (WebException exception)
            {
                var statusCode = TryExtractStatusCode(exception);
                var message = string.IsNullOrWhiteSpace(exception.Message)
                    ? "Request failed."
                    : exception.Message;
                throw new InvalidOperationException(
                    "Live smoke fetch failed: " + message + " (HTTP " + statusCode + ").",
                    exception);
            }
        }

        private static long TryExtractStatusCode(WebException exception)
        {
            if (exception?.Response is HttpWebResponse httpResponse)
            {
                return (long)httpResponse.StatusCode;
            }

            return 0;
        }

        private static string BuildSmokePayload(string matchId)
        {
            return "{" +
                   "\"matchId\":\"" + matchId + "\"," +
                   "\"clockMinute\":12.5," +
                   "\"homeScore\":2," +
                   "\"awayScore\":1" +
                   "}";
        }

        private static void DestroyExistingRuntimeObjects()
        {
            var simHost = UnityEngine.Object.FindFirstObjectByType<GtexSimRuntimeHost>();
            if (simHost != null)
            {
                UnityEngine.Object.DestroyImmediate(simHost.gameObject);
            }

            var liveRuntime = UnityEngine.Object.FindFirstObjectByType<GtexMatchRuntime>();
            if (liveRuntime != null)
            {
                UnityEngine.Object.DestroyImmediate(liveRuntime.gameObject);
            }
        }

        private sealed class MockLiveMatchServer : IDisposable
        {
            private readonly TcpListener listener;
            private readonly Thread serverThread;
            private readonly string responseBody;
            private volatile bool disposed;

            public MockLiveMatchServer(string responseBody)
            {
                this.responseBody = responseBody;
                listener = new TcpListener(IPAddress.Loopback, 0);
                listener.Start();

                var endpoint = (IPEndPoint)listener.LocalEndpoint;
                BaseUrl = "http://127.0.0.1:" + endpoint.Port;

                serverThread = new Thread(ListenLoop)
                {
                    IsBackground = true,
                    Name = "GTEX Live Smoke Server"
                };
                serverThread.Start();
            }

            public string BaseUrl { get; }

            public int RequestCount { get; private set; }

            public string LastRequestPath { get; private set; } = string.Empty;

            public void Dispose()
            {
                if (disposed)
                {
                    return;
                }

                disposed = true;
                listener.Stop();
                serverThread.Join(TimeSpan.FromSeconds(1));
            }

            private void ListenLoop()
            {
                while (!disposed)
                {
                    try
                    {
                        if (!listener.Pending())
                        {
                            Thread.Sleep(10);
                            continue;
                        }

                        using var client = listener.AcceptTcpClient();
                        HandleClient(client);
                    }
                    catch (SocketException)
                    {
                        if (disposed)
                        {
                            return;
                        }
                    }
                    catch (ObjectDisposedException)
                    {
                        return;
                    }
                }
            }

            private void HandleClient(TcpClient client)
            {
                RequestCount += 1;
                client.ReceiveTimeout = 2000;
                client.SendTimeout = 2000;

                using var stream = client.GetStream();
                stream.ReadTimeout = 2000;
                stream.WriteTimeout = 2000;

                var requestBytes = ReadRequestHeader(stream);
                if (requestBytes.Length > 0)
                {
                    var requestText = Encoding.ASCII.GetString(requestBytes);
                    var requestLineEnd = requestText.IndexOf("\r\n", StringComparison.Ordinal);
                    var requestLine = requestLineEnd >= 0
                        ? requestText.Substring(0, requestLineEnd)
                        : requestText.Trim();

                    if (!string.IsNullOrWhiteSpace(requestLine))
                    {
                        var parts = requestLine.Split(' ');
                        if (parts.Length >= 2)
                        {
                            LastRequestPath = parts[1];
                        }
                    }
                }

                var bodyBytes = Encoding.UTF8.GetBytes(responseBody);
                var headerBytes = Encoding.ASCII.GetBytes(
                    "HTTP/1.1 200 OK\r\n" +
                    "Content-Type: application/json\r\n" +
                    "Content-Length: " + bodyBytes.Length + "\r\n" +
                    "Connection: close\r\n\r\n");

                stream.Write(headerBytes, 0, headerBytes.Length);
                stream.Write(bodyBytes, 0, bodyBytes.Length);
                stream.Flush();
            }

            private static byte[] ReadRequestHeader(NetworkStream stream)
            {
                var buffer = new byte[4096];
                var bytesReadTotal = 0;

                while (bytesReadTotal < buffer.Length)
                {
                    int bytesRead;
                    try
                    {
                        bytesRead = stream.Read(buffer, bytesReadTotal, buffer.Length - bytesReadTotal);
                    }
                    catch (IOException)
                    {
                        break;
                    }

                    if (bytesRead <= 0)
                    {
                        break;
                    }

                    bytesReadTotal += bytesRead;
                    if (bytesReadTotal >= 4 &&
                        EndsWithHeaderTerminator(buffer, bytesReadTotal))
                    {
                        break;
                    }
                }

                if (bytesReadTotal <= 0)
                {
                    return Array.Empty<byte>();
                }

                var requestBytes = new byte[bytesReadTotal];
                Buffer.BlockCopy(buffer, 0, requestBytes, 0, bytesReadTotal);
                return requestBytes;
            }

            private static bool EndsWithHeaderTerminator(byte[] buffer, int length)
            {
                if (length < 4)
                {
                    return false;
                }

                return buffer[length - 4] == '\r' &&
                       buffer[length - 3] == '\n' &&
                       buffer[length - 2] == '\r' &&
                       buffer[length - 1] == '\n';
            }
        }
    }
}
#endif
