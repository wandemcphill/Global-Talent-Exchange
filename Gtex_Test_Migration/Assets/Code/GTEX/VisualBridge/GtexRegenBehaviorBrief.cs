using System;
using UnityEngine;

namespace FStudio.GTEX.VisualBridge
{
    /// <summary>
    /// Match-side personality modifiers for unique regens.
    /// Sourced from GET /api/players/{id}/behavior-brief.
    /// Batchmode-safe: missing briefs are no-ops.
    /// </summary>
    [Serializable]
    public sealed class GtexRegenBehaviorBrief
    {
        public string playerId;
        [Range(0f, 1f)] public float riskAppetite = 0.5f;
        [Range(0f, 1f)] public float pressingIntensity = 0.5f;
        [Range(0f, 1f)] public float bigGameNerves = 0.35f;
        [Range(0f, 1f)] public float celebrationHunger = 0.4f;
        [Range(0f, 1f)] public float captaincyWillingness = 0.55f;
        [Range(0f, 1f)] public float shotGreed = 0.45f;
        [Range(0f, 1f)] public float disciplineRisk = 0.35f;
        public string[] notes = Array.Empty<string>();

        public static GtexRegenBehaviorBrief Neutral(string playerId)
        {
            return new GtexRegenBehaviorBrief { playerId = playerId ?? string.Empty };
        }

        public float ShotDecisionBias => Mathf.Lerp(-0.08f, 0.14f, shotGreed);
        public float FoulRiskBias => Mathf.Lerp(-0.05f, 0.18f, disciplineRisk);
        public float BigMomentConfidence => Mathf.Clamp01(1f - bigGameNerves);
        public bool MayRefuseCaptaincy => captaincyWillingness < 0.35f;
    }

    /// <summary>
    /// Applies living-star briefs onto VisualBridge intent without owning football authority.
    /// </summary>
    public static class GtexRegenBehaviorBriefApplier
    {
        public static void Apply(
            GtexRegenBehaviorBrief brief,
            ref float riskModifier,
            ref float pressModifier,
            ref float composureModifier)
        {
            if (brief == null)
            {
                return;
            }

            riskModifier = Mathf.Clamp(riskModifier * Mathf.Lerp(0.9f, 1.18f, brief.riskAppetite), 0.75f, 1.35f);
            pressModifier = Mathf.Clamp(pressModifier * Mathf.Lerp(0.88f, 1.22f, brief.pressingIntensity), 0.75f, 1.35f);
            composureModifier = Mathf.Clamp(
                composureModifier * Mathf.Lerp(0.7f, 1.15f, brief.BigMomentConfidence),
                0.55f,
                1.25f);
        }
    }
}
