using System;
using System.Collections.Generic;
using UnityEngine;

namespace FStudio.GTEX.Illusion
{
    public sealed class GtexIllusionTimelineValidationResult
    {
        public GtexIllusionTimeline Timeline;
        public int AcceptedEvents;
        public int SkippedEvents;
        public int WarningCount;
        public string Summary = string.Empty;

        public bool IsValid => Timeline != null && Timeline.events != null && Timeline.events.Length > 0;
    }

    public static class GtexIllusionTimelineValidator
    {
        public static GtexIllusionTimelineValidationResult Validate(
            GtexIllusionTimeline source,
            string fallbackHomeTeam,
            string fallbackAwayTeam)
        {
            var result = new GtexIllusionTimelineValidationResult();
            if (source == null)
            {
                result.Summary = "Timeline is null.";
                result.WarningCount = 1;
                return result;
            }

            var accepted = new List<GtexIllusionTimelineEvent>();
            var sourceEvents = source.events ?? Array.Empty<GtexIllusionTimelineEvent>();
            for (var index = 0; index < sourceEvents.Length; index += 1)
            {
                if (TrySanitizeEvent(sourceEvents[index], index, out var sanitized, out var warning))
                {
                    accepted.Add(sanitized);
                }
                else
                {
                    result.SkippedEvents += 1;
                }

                if (!string.IsNullOrWhiteSpace(warning))
                {
                    result.WarningCount += 1;
                    Debug.LogWarning("[GTEX Illusion] Timeline validation: " + warning);
                }
            }

            accepted.Sort((left, right) => left.minute.CompareTo(right.minute));

            result.AcceptedEvents = accepted.Count;
            result.Timeline = new GtexIllusionTimeline
            {
                matchId = string.IsNullOrWhiteSpace(source.matchId) ? "illusion-match" : source.matchId.Trim(),
                homeTeam = ResolveName(source.homeTeam, fallbackHomeTeam, "Home"),
                awayTeam = ResolveName(source.awayTeam, fallbackAwayTeam, "Away"),
                seed = source.seed == 0 ? 1337 : source.seed,
                events = accepted.ToArray()
            };
            result.Summary =
                "accepted=" + result.AcceptedEvents +
                " skipped=" + result.SkippedEvents +
                " warnings=" + result.WarningCount;
            return result;
        }

        private static bool TrySanitizeEvent(
            GtexIllusionTimelineEvent source,
            int index,
            out GtexIllusionTimelineEvent sanitized,
            out string warning)
        {
            sanitized = null;
            warning = string.Empty;
            if (source == null)
            {
                warning = "event " + index + " is null.";
                return false;
            }

            var kind = GtexIllusionSceneBuilder.ParseEventKind(source.type);
            if (kind == GtexIllusionEventKind.Unknown)
            {
                warning = "event " + index + " has unsupported type '" + source.type + "'.";
                return false;
            }

            var team = NormalizeTeam(source.team);
            var actorUid = FirstNonEmpty(source.player, source.from);
            var targetUid = FirstNonEmpty(source.to, source.target);

            if (!ValidateParticipants(kind, team, actorUid, targetUid, index, out var participantWarning))
            {
                warning = participantWarning;
                return false;
            }

            if (string.IsNullOrWhiteSpace(team))
            {
                team = InferTeam(actorUid, targetUid);
            }

            sanitized = new GtexIllusionTimelineEvent
            {
                minute = Mathf.Clamp(source.minute, 0f, 90f),
                type = NormalizeType(source.type),
                team = string.IsNullOrWhiteSpace(team) ? "home" : team,
                from = NormalizeUid(source.from),
                to = NormalizeUid(source.to),
                player = NormalizeUid(source.player),
                target = NormalizeUid(source.target),
                outcome = NormalizeOutcome(source.outcome),
                commentary = source.commentary ?? string.Empty,
                overlay = source.overlay ?? string.Empty,
                duration = Mathf.Clamp(source.duration, 0f, 8f),
                x = Mathf.Clamp(source.x, -52.5f, 52.5f),
                z = Mathf.Clamp(source.z, -34f, 34f)
            };

            if (kind == GtexIllusionEventKind.Save && string.IsNullOrWhiteSpace(sanitized.player))
            {
                sanitized.player = sanitized.team + "-1";
            }

            if (kind == GtexIllusionEventKind.Goal && string.IsNullOrWhiteSpace(sanitized.player))
            {
                sanitized.player = FirstNonEmpty(sanitized.from, sanitized.to);
            }

            return true;
        }

        private static bool ValidateParticipants(
            GtexIllusionEventKind kind,
            string team,
            string actorUid,
            string targetUid,
            int index,
            out string warning)
        {
            warning = string.Empty;
            switch (kind)
            {
                case GtexIllusionEventKind.Pass:
                case GtexIllusionEventKind.ThroughPass:
                    if (!IsValidUid(actorUid) || !IsValidUid(targetUid))
                    {
                        warning = "event " + index + " pass requires side-qualified from/to ids.";
                        return false;
                    }

                    if (!SameTeam(actorUid, targetUid))
                    {
                        warning = "event " + index + " pass crosses teams and was skipped.";
                        return false;
                    }

                    if (!TeamMatches(team, actorUid))
                    {
                        warning = "event " + index + " pass team does not match actor uid.";
                        return false;
                    }

                    return true;

                case GtexIllusionEventKind.Dribble:
                case GtexIllusionEventKind.Shot:
                    if (!IsValidUid(actorUid))
                    {
                        warning = "event " + index + " " + kind + " requires a side-qualified player id.";
                        return false;
                    }

                    if (!TeamMatches(team, actorUid))
                    {
                        warning = "event " + index + " " + kind + " team does not match actor uid.";
                        return false;
                    }

                    return true;

                case GtexIllusionEventKind.Tackle:
                case GtexIllusionEventKind.Foul:
                    if (!IsValidUid(actorUid))
                    {
                        warning = "event " + index + " " + kind + " requires a side-qualified actor id.";
                        return false;
                    }

                    if (!string.IsNullOrWhiteSpace(targetUid) && !IsValidUid(targetUid))
                    {
                        warning = "event " + index + " target id is invalid.";
                        return false;
                    }

                    if (!TeamMatches(team, actorUid))
                    {
                        warning = "event " + index + " " + kind + " team does not match actor uid.";
                        return false;
                    }

                    return true;

                case GtexIllusionEventKind.Save:
                case GtexIllusionEventKind.Goal:
                case GtexIllusionEventKind.Commentary:
                case GtexIllusionEventKind.Reset:
                    return true;

                default:
                    return true;
            }
        }

        private static string NormalizeType(string value)
        {
            return (value ?? string.Empty).Trim().ToLowerInvariant().Replace("-", "_");
        }

        private static string NormalizeTeam(string value)
        {
            var normalized = (value ?? string.Empty).Trim().ToLowerInvariant();
            return normalized == "home" || normalized == "away" ? normalized : string.Empty;
        }

        private static string NormalizeUid(string value)
        {
            return IsValidUid(value) ? value.Trim().ToLowerInvariant() : string.Empty;
        }

        private static string NormalizeOutcome(string value)
        {
            var normalized = (value ?? string.Empty).Trim().ToLowerInvariant();
            switch (normalized)
            {
                case "goal":
                case "save":
                case "miss":
                case "blocked":
                    return normalized;
                default:
                    return string.Empty;
            }
        }

        private static bool IsValidUid(string value)
        {
            if (string.IsNullOrWhiteSpace(value))
            {
                return false;
            }

            var normalized = value.Trim().ToLowerInvariant();
            var prefix = normalized.StartsWith("home-", StringComparison.Ordinal)
                ? "home-"
                : normalized.StartsWith("away-", StringComparison.Ordinal)
                    ? "away-"
                    : string.Empty;
            if (string.IsNullOrWhiteSpace(prefix))
            {
                return false;
            }

            var numberPart = normalized.Substring(prefix.Length);
            if (!int.TryParse(numberPart, out var number))
            {
                return false;
            }

            return number >= 1 && number <= 11;
        }

        private static bool TeamMatches(string team, string uid)
        {
            if (string.IsNullOrWhiteSpace(team) || string.IsNullOrWhiteSpace(uid))
            {
                return true;
            }

            return uid.StartsWith(team + "-", StringComparison.OrdinalIgnoreCase);
        }

        private static bool SameTeam(string leftUid, string rightUid)
        {
            return InferTeam(leftUid, string.Empty) == InferTeam(rightUid, string.Empty);
        }

        private static string InferTeam(string primaryUid, string fallbackUid)
        {
            var uid = FirstNonEmpty(primaryUid, fallbackUid).Trim().ToLowerInvariant();
            if (uid.StartsWith("away-", StringComparison.Ordinal))
            {
                return "away";
            }

            return uid.StartsWith("home-", StringComparison.Ordinal) ? "home" : string.Empty;
        }

        private static string FirstNonEmpty(params string[] values)
        {
            if (values == null)
            {
                return string.Empty;
            }

            for (var index = 0; index < values.Length; index += 1)
            {
                if (!string.IsNullOrWhiteSpace(values[index]))
                {
                    return values[index].Trim();
                }
            }

            return string.Empty;
        }

        private static string ResolveName(string preferredName, string fallbackName, string defaultName)
        {
            if (!string.IsNullOrWhiteSpace(preferredName))
            {
                return preferredName.Trim();
            }

            if (!string.IsNullOrWhiteSpace(fallbackName))
            {
                return fallbackName.Trim();
            }

            return defaultName;
        }
    }
}
