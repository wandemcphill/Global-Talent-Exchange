using UnityEngine;

namespace FStudio.GTEX.Simulation
{
    public sealed class GtexSimCrowdController : MonoBehaviour
    {
        [SerializeField] private bool logNeutralEvents;

        private GtexSimEngine engine;

        public int CheerCount { get; private set; }

        public int BooCount { get; private set; }

        public string LastReaction { get; private set; } = string.Empty;

        public float CrowdEnergy { get; private set; }

        public string MoodLabel { get; private set; } = "Waiting";

        public Color ReactionColor { get; private set; } = new Color(0.72f, 0.8f, 0.85f, 1f);

        public void Bind(GtexSimEngine simulationEngine)
        {
            if (ReferenceEquals(engine, simulationEngine))
            {
                return;
            }

            Unbind();
            engine = simulationEngine;

            if (engine == null)
            {
                return;
            }

            engine.EventSystem.EventGenerated += HandleEventGenerated;
            Debug.Log("[GTEX Sim Crowd] Bound to simulation engine.");
        }

        public void Unbind()
        {
            if (engine == null)
            {
                return;
            }

            engine.EventSystem.EventGenerated -= HandleEventGenerated;
            engine = null;
        }

        private void OnDestroy()
        {
            Unbind();
        }

        private void Update()
        {
            if (CrowdEnergy <= 0f)
            {
                CrowdEnergy = 0f;
                if (MoodLabel != "Idle")
                {
                    MoodLabel = "Idle";
                    ReactionColor = new Color(0.72f, 0.8f, 0.85f, 1f);
                }

                return;
            }

            CrowdEnergy = Mathf.Max(0f, CrowdEnergy - (Time.unscaledDeltaTime * 0.18f));
        }

        private void HandleEventGenerated(GtexSimEvent matchEvent)
        {
            if (matchEvent is GtexGoalEvent goalEvent)
            {
                CheerCount += 1;
                LastReaction = "CHEER for " + goalEvent.ScoringTeam + " goal.";
                MoodLabel = "Cheer";
                CrowdEnergy = 1f;
                ReactionColor = new Color(0.35f, 0.88f, 0.53f, 1f);
                Debug.Log("[GTEX Sim Crowd] " + LastReaction);
                return;
            }

            if (matchEvent is GtexFoulEvent foulEvent)
            {
                BooCount += 1;
                LastReaction = "BOO for " + foulEvent.Team + " foul.";
                MoodLabel = "Boo";
                CrowdEnergy = Mathf.Max(CrowdEnergy, 0.72f);
                ReactionColor = new Color(0.94f, 0.56f, 0.24f, 1f);
                Debug.Log("[GTEX Sim Crowd] " + LastReaction);
                return;
            }

            MoodLabel = "Watching";
            CrowdEnergy = Mathf.Max(CrowdEnergy, 0.28f);
            ReactionColor = new Color(0.64f, 0.82f, 0.95f, 1f);

            if (!logNeutralEvents)
            {
                return;
            }

            LastReaction = "Idle on " + matchEvent.GetType().Name + ".";
            Debug.Log("[GTEX Sim Crowd] " + LastReaction);
        }
    }
}
