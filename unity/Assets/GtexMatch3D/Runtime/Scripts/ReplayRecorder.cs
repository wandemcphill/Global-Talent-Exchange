using System;
using System.Collections.Generic;
using UnityEngine;

namespace Gtex.Match3D.Runtime
{
    public sealed class ReplayRecorder : MonoBehaviour
    {
        [SerializeField] private int maxFrames = 1800;
        [SerializeField] private int sampleRate = 30;
        [SerializeField] private int highlightLookBehindFrames = 90;
        [SerializeField] private int highlightLookAheadFrames = 60;

        private readonly List<ReplayFrameData> _frames = new List<ReplayFrameData>();

        private PendingHighlight _pendingHighlight;
        private ReplayClip _readyHighlight;
        private string _lastRecordedFrameId;

        [Serializable]
        private sealed class PendingHighlight
        {
            public int centerIndex;
            public int lookBehind;
            public int lookAhead;
            public string label;
            public string eventId;
        }

        public IReadOnlyList<ReplayFrameData> Frames
        {
            get { return _frames; }
        }

        public int SampleRate
        {
            get { return sampleRate; }
        }

        public void Clear()
        {
            _frames.Clear();
            _pendingHighlight = null;
            _readyHighlight = null;
            _lastRecordedFrameId = null;
        }

        public void RecordFrame(
            MatchSceneSyncPayload payload,
            Dictionary<string, PlayerController> players,
            BallController ball,
            CameraController camera)
        {
            if (payload == null)
            {
                return;
            }

            if (!string.IsNullOrWhiteSpace(payload.frameId) &&
                string.Equals(_lastRecordedFrameId, payload.frameId, StringComparison.Ordinal))
            {
                return;
            }

            _lastRecordedFrameId = payload.frameId;

            ReplayFrameData frame = new ReplayFrameData();
            frame.tick = _frames.Count;
            frame.frameId = payload.frameId;
            frame.clockMinute = payload.clockMinute;
            frame.homeScore = payload.homeScore;
            frame.awayScore = payload.awayScore;
            frame.actionType = payload.action != null ? payload.action.type : null;
            frame.actionLabel = payload.action != null ? payload.action.label : null;

            if (players != null)
            {
                foreach (KeyValuePair<string, PlayerController> entry in players)
                {
                    if (entry.Value == null || !entry.Value.gameObject.activeSelf)
                    {
                        continue;
                    }

                    frame.players.Add(Clone(entry.Value.BuildReplayFrame()));
                }
            }

            if (ball != null)
            {
                frame.ball = Clone(ball.BuildReplayFrame());
            }

            if (camera != null)
            {
                frame.camera = Clone(camera.BuildReplayFrame());
            }

            _frames.Add(frame);
            TrimFrames();
            UpdatePendingHighlight();
        }

        public void MarkHighlightFromPayload(MatchSceneSyncPayload payload)
        {
            if (payload == null || payload.matchEvent == null)
            {
                return;
            }

            if (!IsHighlightEvent(payload.matchEvent.type))
            {
                return;
            }

            _pendingHighlight = new PendingHighlight();
            _pendingHighlight.centerIndex = Mathf.Max(0, _frames.Count - 1);
            _pendingHighlight.lookBehind = highlightLookBehindFrames;
            _pendingHighlight.lookAhead = highlightLookAheadFrames;
            _pendingHighlight.label = string.IsNullOrWhiteSpace(payload.matchEvent.bannerText)
                ? payload.matchEvent.type
                : payload.matchEvent.bannerText;
            _pendingHighlight.eventId = payload.matchEvent.id;
        }

        public ReplayClip ConsumeReadyHighlight()
        {
            ReplayClip clip = _readyHighlight;
            _readyHighlight = null;
            return clip;
        }

        public ReplayClip BuildRecentClip(int frameCount, string label)
        {
            int end = _frames.Count - 1;
            if (end < 0)
            {
                return null;
            }

            int start = Mathf.Max(0, end - Mathf.Max(0, frameCount) + 1);
            return BuildClip(start, end, label);
        }

        private void UpdatePendingHighlight()
        {
            if (_pendingHighlight == null)
            {
                return;
            }

            if ((_frames.Count - 1) < (_pendingHighlight.centerIndex + _pendingHighlight.lookAhead))
            {
                return;
            }

            int start = Mathf.Max(0, _pendingHighlight.centerIndex - _pendingHighlight.lookBehind);
            int end = Mathf.Min(_frames.Count - 1, _pendingHighlight.centerIndex + _pendingHighlight.lookAhead);
            _readyHighlight = BuildClip(start, end, _pendingHighlight.label);
            _pendingHighlight = null;
        }

        private ReplayClip BuildClip(int startIndex, int endIndex, string label)
        {
            if (_frames.Count == 0 || startIndex > endIndex)
            {
                return null;
            }

            ReplayClip clip = new ReplayClip();
            clip.label = label;
            clip.framesPerSecond = Mathf.Max(1, sampleRate);

            for (int index = startIndex; index <= endIndex; index += 1)
            {
                clip.frames.Add(Clone(_frames[index]));
            }

            return clip;
        }

        private void TrimFrames()
        {
            while (_frames.Count > maxFrames)
            {
                _frames.RemoveAt(0);
                if (_pendingHighlight != null)
                {
                    _pendingHighlight.centerIndex = Mathf.Max(0, _pendingHighlight.centerIndex - 1);
                }
            }
        }

        private static bool IsHighlightEvent(string eventType)
        {
            if (string.IsNullOrWhiteSpace(eventType))
            {
                return false;
            }

            return string.Equals(eventType, "goal", StringComparison.OrdinalIgnoreCase) ||
                   string.Equals(eventType, "save", StringComparison.OrdinalIgnoreCase) ||
                   string.Equals(eventType, "miss", StringComparison.OrdinalIgnoreCase);
        }

        private static ReplayFrameData Clone(ReplayFrameData source)
        {
            ReplayFrameData clone = new ReplayFrameData();
            clone.tick = source.tick;
            clone.frameId = source.frameId;
            clone.clockMinute = source.clockMinute;
            clone.homeScore = source.homeScore;
            clone.awayScore = source.awayScore;
            clone.actionType = source.actionType;
            clone.actionLabel = source.actionLabel;
            clone.ball = Clone(source.ball);
            clone.camera = Clone(source.camera);
            for (int index = 0; index < source.players.Count; index += 1)
            {
                clone.players.Add(Clone(source.players[index]));
            }

            return clone;
        }

        private static ReplayPlayerFrameData Clone(ReplayPlayerFrameData source)
        {
            ReplayPlayerFrameData clone = new ReplayPlayerFrameData();
            clone.id = source.id;
            clone.position = source.position;
            clone.rotation = source.rotation;
            clone.velocity = source.velocity;
            clone.animationState = source.animationState;
            clone.highlighted = source.highlighted;
            clone.hasPossession = source.hasPossession;
            return clone;
        }

        private static ReplayBallFrameData Clone(ReplayBallFrameData source)
        {
            ReplayBallFrameData clone = new ReplayBallFrameData();
            clone.position = source.position;
            clone.rotation = source.rotation;
            clone.velocity = source.velocity;
            clone.spin = source.spin;
            clone.state = source.state;
            clone.trajectoryType = source.trajectoryType;
            return clone;
        }

        private static ReplayCameraFrameData Clone(ReplayCameraFrameData source)
        {
            ReplayCameraFrameData clone = new ReplayCameraFrameData();
            clone.position = source.position;
            clone.target = source.target;
            clone.mode = source.mode;
            clone.projectionPreset = source.projectionPreset;
            return clone;
        }
    }
}
