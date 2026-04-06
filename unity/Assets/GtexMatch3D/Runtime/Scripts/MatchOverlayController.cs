using System.Collections.Generic;
using UnityEngine;

namespace Gtex.Match3D.Runtime
{
    public sealed class MatchOverlayController : MonoBehaviour
    {
        [SerializeField] private int maxFeedEntries = 8;
        [SerializeField] private Rect scoreRect = new Rect(16f, 16f, 420f, 88f);
        [SerializeField] private Rect headlineRect = new Rect(16f, 110f, 760f, 56f);
        [SerializeField] private Rect feedRect = new Rect(16f, 176f, 520f, 220f);

        private readonly List<string> _feedEntries = new List<string>();

        private GUIStyle _scoreStyle;
        private GUIStyle _clockStyle;
        private GUIStyle _headlineStyle;
        private GUIStyle _feedStyle;
        private GUIStyle _panelStyle;
        private string _homeTeamName = "Home";
        private string _awayTeamName = "Away";
        private int _homeScore;
        private int _awayScore;
        private float _clockMinute;
        private string _phase = "live";
        private string _headlineText = string.Empty;
        private float _headlineUntilTime;

        private void Update()
        {
            if (!string.IsNullOrEmpty(_headlineText) &&
                Time.unscaledTime >= _headlineUntilTime)
            {
                _headlineText = string.Empty;
            }
        }

        private void OnGUI()
        {
            EnsureStyles();

            string scoreLine = _homeTeamName + " " + _homeScore + " - " + _awayScore + " " + _awayTeamName;
            GUI.Box(scoreRect, GUIContent.none, _panelStyle);
            GUI.Label(
                new Rect(scoreRect.x + 14f, scoreRect.y + 10f, scoreRect.width - 28f, 36f),
                scoreLine,
                _scoreStyle);
            GUI.Label(
                new Rect(scoreRect.x + 14f, scoreRect.y + 46f, scoreRect.width - 28f, 24f),
                BuildClockLabel(),
                _clockStyle);

            if (!string.IsNullOrEmpty(_headlineText))
            {
                GUI.Box(headlineRect, GUIContent.none, _panelStyle);
                GUI.Label(
                    new Rect(headlineRect.x + 14f, headlineRect.y + 10f, headlineRect.width - 28f, 32f),
                    _headlineText,
                    _headlineStyle);
            }

            GUI.Box(feedRect, GUIContent.none, _panelStyle);
            GUI.Label(
                new Rect(feedRect.x + 14f, feedRect.y + 10f, feedRect.width - 28f, 24f),
                "Event Feed",
                _clockStyle);

            Rect textRect = new Rect(feedRect.x + 14f, feedRect.y + 38f, feedRect.width - 28f, feedRect.height - 50f);
            GUI.Label(textRect, BuildFeedText(), _feedStyle);
        }

        public void ConfigureTeams(string homeTeamName, string awayTeamName)
        {
            if (!string.IsNullOrWhiteSpace(homeTeamName))
            {
                _homeTeamName = homeTeamName.Trim();
            }

            if (!string.IsNullOrWhiteSpace(awayTeamName))
            {
                _awayTeamName = awayTeamName.Trim();
            }
        }

        public void UpdateScore(int homeScore, int awayScore)
        {
            _homeScore = Mathf.Max(0, homeScore);
            _awayScore = Mathf.Max(0, awayScore);
        }

        public void UpdateClock(float clockMinute)
        {
            _clockMinute = Mathf.Max(0f, clockMinute);
        }

        public void SetPhase(string phase)
        {
            if (!string.IsNullOrWhiteSpace(phase))
            {
                _phase = phase.Trim();
            }
        }

        public void ShowHeadline(string text, float durationSeconds = 2.2f)
        {
            if (string.IsNullOrWhiteSpace(text))
            {
                return;
            }

            _headlineText = text.Trim();
            _headlineUntilTime = Time.unscaledTime + Mathf.Max(0.5f, durationSeconds);
        }

        public void PushEvent(string text)
        {
            if (string.IsNullOrWhiteSpace(text))
            {
                return;
            }

            _feedEntries.Insert(0, text.Trim());
            if (_feedEntries.Count > maxFeedEntries)
            {
                _feedEntries.RemoveAt(_feedEntries.Count - 1);
            }
        }

        public void ResetOverlay()
        {
            _homeTeamName = "Home";
            _awayTeamName = "Away";
            _homeScore = 0;
            _awayScore = 0;
            _clockMinute = 0f;
            _phase = "live";
            _headlineText = string.Empty;
            _headlineUntilTime = 0f;
            _feedEntries.Clear();
        }

        private string BuildClockLabel()
        {
            int wholeMinutes = Mathf.FloorToInt(_clockMinute);
            int seconds = Mathf.Clamp(Mathf.FloorToInt((_clockMinute - wholeMinutes) * 60f), 0, 59);
            string phaseLabel = string.IsNullOrWhiteSpace(_phase) ? "LIVE" : _phase.ToUpperInvariant();
            return string.Format("{0:00}:{1:00}  {2}", wholeMinutes, seconds, phaseLabel);
        }

        private string BuildFeedText()
        {
            if (_feedEntries.Count == 0)
            {
                return "Waiting for live events...";
            }

            return string.Join("\n", _feedEntries.ToArray());
        }

        private void EnsureStyles()
        {
            if (_panelStyle != null)
            {
                return;
            }

            _panelStyle = new GUIStyle(GUI.skin.box);
            _panelStyle.normal.textColor = Color.white;
            _panelStyle.alignment = TextAnchor.UpperLeft;
            _panelStyle.fontSize = 14;

            _scoreStyle = new GUIStyle(GUI.skin.label);
            _scoreStyle.fontSize = 28;
            _scoreStyle.fontStyle = FontStyle.Bold;
            _scoreStyle.normal.textColor = Color.white;

            _clockStyle = new GUIStyle(GUI.skin.label);
            _clockStyle.fontSize = 15;
            _clockStyle.fontStyle = FontStyle.Bold;
            _clockStyle.normal.textColor = new Color(0.82f, 0.92f, 1f);

            _headlineStyle = new GUIStyle(GUI.skin.label);
            _headlineStyle.fontSize = 26;
            _headlineStyle.fontStyle = FontStyle.Bold;
            _headlineStyle.normal.textColor = new Color(1f, 0.92f, 0.55f);

            _feedStyle = new GUIStyle(GUI.skin.label);
            _feedStyle.fontSize = 15;
            _feedStyle.wordWrap = true;
            _feedStyle.normal.textColor = new Color(0.92f, 0.95f, 0.98f);
        }
    }
}
