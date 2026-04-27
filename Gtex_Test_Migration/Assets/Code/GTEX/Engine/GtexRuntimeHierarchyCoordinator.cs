using System;
using System.Collections.Generic;
using FStudio.MatchEngine;
using FStudio.MatchEngine.Balls;
using UnityEngine;

namespace FStudio.GTEX.Engine
{
    public static class GtexRuntimeHierarchyCoordinator
    {
        private const string MatchRootName = "MatchRoot";
        private const string PitchRootName = "PitchRoot";
        private const string GameplayRuntimeRootName = "GameplayRuntime";
        private const string CosmeticEnvironmentRootName = "CosmeticEnvironmentRoot";
        private const string PlayersRootName = "Players";
        private const string BallRootName = "Ball";
        private const string RefereeRootName = "Referee";
        private const string CameraTargetsRootName = "CameraTargets";

        public static void EnsureMatchHierarchy(MatchManager manager, GtexStadiumAtmosphere atmosphere = null)
        {
            if (manager == null)
            {
                return;
            }

            var matchRoot = EnsureRoot(MatchRootName, null);
            var pitchRoot = EnsureRoot(PitchRootName, matchRoot);
            var gameplayRuntimeRoot = EnsureRoot(GameplayRuntimeRootName, matchRoot);
            var cosmeticRoot = EnsureRoot(CosmeticEnvironmentRootName, matchRoot);
            var playersRoot = EnsureRoot(PlayersRootName, gameplayRuntimeRoot);
            var ballRoot = EnsureRoot(BallRootName, gameplayRuntimeRoot);
            var refereeRoot = EnsureRoot(RefereeRootName, gameplayRuntimeRoot);
            EnsureRoot(CameraTargetsRootName, gameplayRuntimeRoot);

            ReparentPitch(manager, pitchRoot);
            ReparentGameplay(manager, playersRoot, ballRoot, refereeRoot);
            ReparentCosmetics(atmosphere, cosmeticRoot);
            DisableCosmeticColliders(cosmeticRoot);
            ValidateCosmeticIsolation(cosmeticRoot, manager);
        }

        public static Transform FindCosmeticEnvironmentRoot()
        {
            return FindSceneTransform(CosmeticEnvironmentRootName);
        }

        public static void SetCosmeticEnvironmentActive(bool value)
        {
            var root = FindCosmeticEnvironmentRoot();
            if (root != null)
            {
                root.gameObject.SetActive(value);
            }
        }

        private static void ReparentPitch(MatchManager manager, Transform pitchRoot)
        {
            var fieldRoot =
                FindSceneTransform("Field") ??
                FindSceneTransform("fieldGround")?.parent ??
                FindSceneTransform("Grass")?.parent;

            if (fieldRoot != null)
            {
                Reparent(fieldRoot, pitchRoot);
            }
            else
            {
                ReparentNamed("fieldGround", pitchRoot);
                ReparentNamed("Grass", pitchRoot);
                ReparentNamed("Lines", pitchRoot);
            }

            if (manager.goalNet1 != null && (fieldRoot == null || !IsDescendantOf(manager.goalNet1.transform, fieldRoot)))
            {
                Reparent(manager.goalNet1.transform, pitchRoot);
            }

            if (manager.goalNet2 != null && (fieldRoot == null || !IsDescendantOf(manager.goalNet2.transform, fieldRoot)))
            {
                Reparent(manager.goalNet2.transform, pitchRoot);
            }

            ReparentNamed("GoalRaycastAreaHome", pitchRoot);
            ReparentNamed("GoalRaycastAreaAway", pitchRoot);
            ReparentNamed("GTEX_ExternalPlaybackFieldUnderlay", pitchRoot);
        }

        private static void ReparentGameplay(MatchManager manager, Transform playersRoot, Transform ballRoot, Transform refereeRoot)
        {
            if (manager.GameTeam1 != null && manager.GameTeam1.GamePlayers != null)
            {
                for (var index = 0; index < manager.GameTeam1.GamePlayers.Length; index += 1)
                {
                    var player = manager.GameTeam1.GamePlayers[index];
                    if (player != null && player.PlayerController != null && player.PlayerController.UnityObject != null)
                    {
                        Reparent(player.PlayerController.UnityObject.transform, playersRoot);
                    }
                }
            }

            if (manager.GameTeam2 != null && manager.GameTeam2.GamePlayers != null)
            {
                for (var index = 0; index < manager.GameTeam2.GamePlayers.Length; index += 1)
                {
                    var player = manager.GameTeam2.GamePlayers[index];
                    if (player != null && player.PlayerController != null && player.PlayerController.UnityObject != null)
                    {
                        Reparent(player.PlayerController.UnityObject.transform, playersRoot);
                    }
                }
            }

            if (manager.Referees != null)
            {
                for (var index = 0; index < manager.Referees.Length; index += 1)
                {
                    var referee = manager.Referees[index];
                    if (referee != null && referee.PlayerController != null && referee.PlayerController.UnityObject != null)
                    {
                        Reparent(referee.PlayerController.UnityObject.transform, refereeRoot);
                    }
                }
            }

            if (Ball.Current != null)
            {
                Reparent(Ball.Current.transform, ballRoot);
            }
        }

        private static void ReparentCosmetics(GtexStadiumAtmosphere atmosphere, Transform cosmeticRoot)
        {
            if (atmosphere != null)
            {
                Reparent(atmosphere.transform, cosmeticRoot);
            }

            var standaloneAtmosphere = UnityEngine.Object.FindFirstObjectByType<GtexStadiumAtmosphere>();
            if (standaloneAtmosphere != null)
            {
                Reparent(standaloneAtmosphere.transform, cosmeticRoot);
            }
        }

        private static void DisableCosmeticColliders(Transform cosmeticRoot)
        {
            if (cosmeticRoot == null)
            {
                return;
            }

            var colliders = cosmeticRoot.GetComponentsInChildren<Collider>(true);
            for (var index = 0; index < colliders.Length; index += 1)
            {
                var collider = colliders[index];
                if (collider != null)
                {
                    collider.enabled = false;
                }
            }
        }

        private static void ValidateCosmeticIsolation(Transform cosmeticRoot, MatchManager manager)
        {
            if (cosmeticRoot == null || manager == null)
            {
                return;
            }

            var invalidChildren = new List<string>();
            if (manager.goalNet1 != null && IsDescendantOf(manager.goalNet1.transform, cosmeticRoot))
            {
                invalidChildren.Add("goalNet1");
            }

            if (manager.goalNet2 != null && IsDescendantOf(manager.goalNet2.transform, cosmeticRoot))
            {
                invalidChildren.Add("goalNet2");
            }

            if (Ball.Current != null && IsDescendantOf(Ball.Current.transform, cosmeticRoot))
            {
                invalidChildren.Add("ball");
            }

            if (invalidChildren.Count == 0)
            {
                return;
            }

            Debug.LogWarning(
                "[GTEX Hierarchy] CosmeticEnvironmentRoot still contains gameplay objects: " +
                string.Join(", ", invalidChildren));
        }

        private static Transform EnsureRoot(string name, Transform parent)
        {
            var existing = parent != null ? parent.Find(name) : FindSceneTransform(name);
            if (existing != null)
            {
                if (parent != null && existing.parent != parent)
                {
                    existing.SetParent(parent, true);
                }

                return existing;
            }

            var gameObject = new GameObject(name);
            var transform = gameObject.transform;
            transform.SetParent(parent, false);
            transform.localPosition = Vector3.zero;
            transform.localRotation = Quaternion.identity;
            transform.localScale = Vector3.one;
            return transform;
        }

        private static void ReparentNamed(string childName, Transform parent)
        {
            var candidate = FindSceneTransform(childName);
            if (candidate != null)
            {
                Reparent(candidate, parent);
            }
        }

        private static void Reparent(Transform child, Transform parent)
        {
            if (child == null || parent == null || child == parent || child.parent == parent)
            {
                return;
            }

            if (IsDescendantOf(parent, child))
            {
                return;
            }

            child.SetParent(parent, true);
        }

        private static Transform FindSceneTransform(string transformName)
        {
            var allTransforms = UnityEngine.Object.FindObjectsByType<Transform>(FindObjectsSortMode.None);
            for (var index = 0; index < allTransforms.Length; index += 1)
            {
                var candidate = allTransforms[index];
                if (candidate != null && string.Equals(candidate.name, transformName, System.StringComparison.Ordinal))
                {
                    return candidate;
                }
            }

            return null;
        }

        private static bool IsDescendantOf(Transform child, Transform ancestor)
        {
            if (child == null || ancestor == null)
            {
                return false;
            }

            var current = child;
            while (current != null)
            {
                if (current == ancestor)
                {
                    return true;
                }

                current = current.parent;
            }

            return false;
        }
    }
}
