using System;

namespace FStudio.GTEX.Illusion
{
    public static class GtexIllusionSceneBuilder
    {
        public static GtexIllusionScene Build(GtexIllusionTimelineEvent source)
        {
            if (source == null)
            {
                source = new GtexIllusionTimelineEvent();
            }

            var kind = ParseEventKind(source.type);
            return new GtexIllusionScene
            {
                EventKind = kind,
                SceneKind = ResolveSceneKind(kind),
                Minute = source.minute,
                TeamId = NormalizeTeam(source.team, source.from, source.player),
                ActorUid = FirstNonEmpty(source.player, source.from),
                TargetUid = FirstNonEmpty(source.to, source.target),
                Outcome = (source.outcome ?? string.Empty).Trim().ToLowerInvariant(),
                Commentary = source.commentary ?? string.Empty,
                Overlay = source.overlay ?? string.Empty,
                DurationSeconds = source.duration > 0f ? source.duration : ResolveDefaultDuration(kind),
                TargetX = source.x,
                TargetZ = source.z
            };
        }

        public static GtexIllusionScene Build(GtexIllusionSceneRecord source)
        {
            if (source == null)
            {
                source = new GtexIllusionSceneRecord();
            }

            var sceneKind = ParseSceneKind(source.type);
            var actorUid = FirstNonEmpty(source.actor, ResolveActor(source.actors, 0));
            var targetUid = FirstNonEmpty(source.target, ResolveActor(source.actors, 1));
            return new GtexIllusionScene
            {
                EventKind = ResolveEventKind(sceneKind),
                SceneKind = sceneKind,
                Minute = source.minute,
                TeamId = NormalizeTeam(source.team, actorUid, actorUid),
                ActorUid = actorUid,
                TargetUid = targetUid,
                Outcome = (source.outcome ?? string.Empty).Trim().ToLowerInvariant(),
                Commentary = source.commentary ?? string.Empty,
                Overlay = source.overlay ?? string.Empty,
                DurationSeconds = source.duration > 0f ? source.duration : ResolveDefaultDuration(ResolveEventKind(sceneKind)),
                TargetX = source.x,
                TargetZ = source.z
            };
        }

        public static GtexIllusionEventKind ParseEventKind(string value)
        {
            switch ((value ?? string.Empty).Trim().ToLowerInvariant().Replace("-", "_"))
            {
                case "commentary":
                case "overlay":
                    return GtexIllusionEventKind.Commentary;
                case "pass":
                case "ground_pass":
                case "groundpass":
                    return GtexIllusionEventKind.Pass;
                case "through":
                case "through_pass":
                case "throughpass":
                case "through_ground":
                case "throughground":
                    return GtexIllusionEventKind.ThroughPass;
                case "carry":
                case "dribble":
                    return GtexIllusionEventKind.Dribble;
                case "shot":
                case "shoot":
                    return GtexIllusionEventKind.Shot;
                case "save":
                case "keeper_save":
                case "keepersave":
                    return GtexIllusionEventKind.Save;
                case "goal":
                    return GtexIllusionEventKind.Goal;
                case "tackle":
                case "interception":
                    return GtexIllusionEventKind.Tackle;
                case "foul":
                    return GtexIllusionEventKind.Foul;
                case "reset":
                case "kickoff":
                    return GtexIllusionEventKind.Reset;
                default:
                    return GtexIllusionEventKind.Unknown;
            }
        }

        private static GtexIllusionSceneKind ResolveSceneKind(GtexIllusionEventKind kind)
        {
            switch (kind)
            {
                case GtexIllusionEventKind.Commentary:
                    return GtexIllusionSceneKind.CommentaryScene;
                case GtexIllusionEventKind.Pass:
                    return GtexIllusionSceneKind.PassScene;
                case GtexIllusionEventKind.ThroughPass:
                    return GtexIllusionSceneKind.ThroughPassScene;
                case GtexIllusionEventKind.Dribble:
                    return GtexIllusionSceneKind.DribbleScene;
                case GtexIllusionEventKind.Shot:
                    return GtexIllusionSceneKind.ShotScene;
                case GtexIllusionEventKind.Save:
                    return GtexIllusionSceneKind.SaveScene;
                case GtexIllusionEventKind.Goal:
                    return GtexIllusionSceneKind.GoalScene;
                case GtexIllusionEventKind.Tackle:
                    return GtexIllusionSceneKind.TackleScene;
                case GtexIllusionEventKind.Foul:
                    return GtexIllusionSceneKind.FoulScene;
                case GtexIllusionEventKind.Reset:
                    return GtexIllusionSceneKind.ResetScene;
                default:
                    return GtexIllusionSceneKind.Unknown;
            }
        }

        public static GtexIllusionSceneKind ParseSceneKind(string value)
        {
            switch ((value ?? string.Empty).Trim().ToLowerInvariant().Replace("-", "_"))
            {
                case "commentary_scene":
                    return GtexIllusionSceneKind.CommentaryScene;
                case "pass_scene":
                    return GtexIllusionSceneKind.PassScene;
                case "through_pass_scene":
                case "through_scene":
                    return GtexIllusionSceneKind.ThroughPassScene;
                case "dribble_scene":
                case "carry_scene":
                    return GtexIllusionSceneKind.DribbleScene;
                case "shot_scene":
                    return GtexIllusionSceneKind.ShotScene;
                case "save_scene":
                    return GtexIllusionSceneKind.SaveScene;
                case "goal_scene":
                    return GtexIllusionSceneKind.GoalScene;
                case "tackle_scene":
                    return GtexIllusionSceneKind.TackleScene;
                case "foul_scene":
                    return GtexIllusionSceneKind.FoulScene;
                case "reset_scene":
                    return GtexIllusionSceneKind.ResetScene;
                default:
                    return ResolveSceneKind(ParseEventKind(value));
            }
        }

        private static GtexIllusionEventKind ResolveEventKind(GtexIllusionSceneKind kind)
        {
            switch (kind)
            {
                case GtexIllusionSceneKind.CommentaryScene:
                    return GtexIllusionEventKind.Commentary;
                case GtexIllusionSceneKind.PassScene:
                    return GtexIllusionEventKind.Pass;
                case GtexIllusionSceneKind.ThroughPassScene:
                    return GtexIllusionEventKind.ThroughPass;
                case GtexIllusionSceneKind.DribbleScene:
                    return GtexIllusionEventKind.Dribble;
                case GtexIllusionSceneKind.ShotScene:
                    return GtexIllusionEventKind.Shot;
                case GtexIllusionSceneKind.SaveScene:
                    return GtexIllusionEventKind.Save;
                case GtexIllusionSceneKind.GoalScene:
                    return GtexIllusionEventKind.Goal;
                case GtexIllusionSceneKind.TackleScene:
                    return GtexIllusionEventKind.Tackle;
                case GtexIllusionSceneKind.FoulScene:
                    return GtexIllusionEventKind.Foul;
                case GtexIllusionSceneKind.ResetScene:
                    return GtexIllusionEventKind.Reset;
                default:
                    return GtexIllusionEventKind.Unknown;
            }
        }

        private static float ResolveDefaultDuration(GtexIllusionEventKind kind)
        {
            switch (kind)
            {
                case GtexIllusionEventKind.Pass:
                    return 1.1f;
                case GtexIllusionEventKind.ThroughPass:
                    return 1.25f;
                case GtexIllusionEventKind.Dribble:
                    return 1.4f;
                case GtexIllusionEventKind.Shot:
                    return 1.2f;
                case GtexIllusionEventKind.Save:
                case GtexIllusionEventKind.Goal:
                    return 1.35f;
                case GtexIllusionEventKind.Tackle:
                case GtexIllusionEventKind.Foul:
                    return 1f;
                default:
                    return 0.75f;
            }
        }

        private static string NormalizeTeam(string team, string fromUid, string playerUid)
        {
            var normalized = (team ?? string.Empty).Trim().ToLowerInvariant();
            if (normalized == "home" || normalized == "away")
            {
                return normalized;
            }

            var uid = FirstNonEmpty(fromUid, playerUid);
            if (uid.StartsWith("home-", StringComparison.OrdinalIgnoreCase))
            {
                return "home";
            }

            if (uid.StartsWith("away-", StringComparison.OrdinalIgnoreCase))
            {
                return "away";
            }

            return "home";
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

        private static string ResolveActor(string[] actors, int index)
        {
            if (actors == null || index < 0 || index >= actors.Length)
            {
                return string.Empty;
            }

            return actors[index] ?? string.Empty;
        }
    }
}
