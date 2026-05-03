using System.Collections.Generic;
using UnityEngine;

namespace FStudio.GTEX.VisualBridge
{
    public enum GtexVisualSequenceCompletionMode
    {
        Auto,
        DelayOnly,
        Possession,
        PlayerAtPoint,
        PassReceived,
        ThroughPassReachable,
        ShotReleased,
        KeeperOutcome
    }

    public sealed class GtexVisualSequenceStep
    {
        public GtexVisualCommand command;
        public float delayAfterSeconds = 0.15f;
        public bool required = true;
        public string label = string.Empty;
        public float timeoutSeconds = 3f;
        public GtexVisualSequenceCompletionMode completionMode = GtexVisualSequenceCompletionMode.Auto;
        public string completionPlayerUid = string.Empty;
        public Vector3 completionWorldPosition;
        public float completionDistance = 1.5f;
        public bool evaluateShotOutcome;
    }

    public sealed class GtexVisualSequencePositionTarget
    {
        public string playerUid = string.Empty;
        public Vector3 targetWorldPosition;
        public float thresholdDistance = 2f;
        public float urgency = 1f;
        public string readyLabel = string.Empty;
    }

    public sealed class GtexVisualSequence
    {
        public string sequenceId = string.Empty;
        public string teamId = string.Empty;
        public readonly List<string> controlledPlayerUids = new List<string>();
        public float leaseDurationSeconds = 6f;
        public string preSequenceBallOwnerUid = string.Empty;
        public float preSequenceTimeoutSeconds = 14f;
        public readonly List<GtexVisualSequencePositionTarget> preSequencePositions = new List<GtexVisualSequencePositionTarget>();
        public readonly List<GtexVisualSequenceStep> steps = new List<GtexVisualSequenceStep>();
    }
}
