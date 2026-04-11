using System;

namespace FStudio.GTEX
{
    [Serializable]
    public sealed class GtexLiveAccessGrant
    {
        public string match_id = string.Empty;
        public string spectator_session_id = string.Empty;
        public string access_token = string.Empty;
        public string refresh_token = string.Empty;
        public string token_type = "bearer";
        public int expires_in;
        public int refresh_expires_in;
        public string live_path = string.Empty;
        public string websocket_path = string.Empty;
        public string refresh_path = string.Empty;

        public bool HasAccessToken => !string.IsNullOrWhiteSpace(access_token);

        public bool HasRefreshToken => !string.IsNullOrWhiteSpace(refresh_token);
    }
}
