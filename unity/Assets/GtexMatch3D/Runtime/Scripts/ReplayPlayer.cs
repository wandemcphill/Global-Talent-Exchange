using UnityEngine;

namespace Gtex.Match3D.Runtime
{
    public sealed class ReplayPlayer : MonoBehaviour
    {
        [SerializeField] private MatchController matchController;
        [SerializeField] private bool pauseLiveSyncWhilePlaying = true;
        [SerializeField] private bool useGlobalTimeScale = true;
        [SerializeField] private float slowMotionTimeScale = 0.35f;

        private ReplayClip _activeClip;
        private int _frameIndex;
        private float _frameAccumulator;
        private float _playbackSpeed = 1f;
        private bool _loop;
        private bool _paused;
        private bool _slowMotion;
        private float _previousTimeScale = 1f;
        private bool _timeScaleCaptured;

        public bool IsPlaying
        {
            get { return _activeClip != null && _activeClip.frames != null && _activeClip.frames.Count > 0; }
        }

        public bool IgnoreLiveSync
        {
            get { return pauseLiveSyncWhilePlaying && IsPlaying; }
        }

        private void Awake()
        {
            if (matchController == null)
            {
                matchController = GetComponent<MatchController>();
            }
        }

        private void Update()
        {
            if (!IsPlaying || _paused)
            {
                return;
            }

            if (_activeClip.frames.Count <= 1)
            {
                return;
            }

            _frameAccumulator += Time.unscaledDeltaTime * _playbackSpeed * Mathf.Max(1, _activeClip.framesPerSecond);
            while (_frameAccumulator >= 1f)
            {
                _frameAccumulator -= 1f;
                _frameIndex += 1;
                if (_frameIndex >= _activeClip.frames.Count)
                {
                    if (_loop)
                    {
                        _frameIndex = 0;
                    }
                    else
                    {
                        Stop();
                        return;
                    }
                }

                ApplyCurrentFrame(false);
            }
        }

        public void SetMatchController(MatchController controller)
        {
            matchController = controller;
        }

        public void Play(ReplayClip clip, bool loop, float playbackSpeed, bool slowMotion)
        {
            if (clip == null || clip.frames == null || clip.frames.Count == 0)
            {
                return;
            }

            _activeClip = clip;
            _loop = loop;
            _paused = false;
            _slowMotion = slowMotion;
            _playbackSpeed = Mathf.Max(0.10f, playbackSpeed);
            _frameIndex = 0;
            _frameAccumulator = 0f;
            _timeScaleCaptured = false;

            if (matchController != null)
            {
                matchController.SetReplayMode(true);
            }

            ApplyTimeScale();
            ApplyCurrentFrame(true);
        }

        public void Pause()
        {
            _paused = true;
        }

        public void Resume()
        {
            _paused = false;
        }

        public void Stop()
        {
            _activeClip = null;
            _frameIndex = 0;
            _frameAccumulator = 0f;
            _paused = false;
            RestoreTimeScale();
            _timeScaleCaptured = false;

            if (matchController != null)
            {
                matchController.SetReplayMode(false);
            }
        }

        public void Rewind()
        {
            if (!IsPlaying)
            {
                return;
            }

            _frameIndex = 0;
            _frameAccumulator = 0f;
            ApplyCurrentFrame(true);
        }

        public void SetPlaybackSpeed(float value)
        {
            _playbackSpeed = Mathf.Max(0.10f, value);
        }

        public void SetSlowMotion(bool enabled)
        {
            _slowMotion = enabled;
            ApplyTimeScale();
        }

        private void ApplyCurrentFrame(bool immediate)
        {
            if (!IsPlaying || matchController == null)
            {
                return;
            }

            matchController.ApplyReplayFrame(_activeClip.frames[_frameIndex], immediate);
        }

        private void ApplyTimeScale()
        {
            if (!useGlobalTimeScale)
            {
                return;
            }

            if (!IsPlaying)
            {
                RestoreTimeScale();
                return;
            }

            if (!_timeScaleCaptured)
            {
                _previousTimeScale = Time.timeScale;
                _timeScaleCaptured = true;
            }
            Time.timeScale = _slowMotion ? slowMotionTimeScale : 1f;
        }

        private void RestoreTimeScale()
        {
            if (!useGlobalTimeScale)
            {
                return;
            }

            Time.timeScale = _previousTimeScale <= 0f ? 1f : _previousTimeScale;
            _previousTimeScale = 1f;
        }
    }
}
