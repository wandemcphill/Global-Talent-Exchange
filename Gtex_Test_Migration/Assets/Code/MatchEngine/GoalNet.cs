using UnityEngine;

using FStudio.MatchEngine.Players;
using FStudio.MatchEngine.Balls;

using System.Linq;
using System.Collections.Generic;

namespace FStudio.MatchEngine {
    public class GoalNet : MonoBehaviour {
        [SerializeField] private Transform middlePoint = default;

        public GameObject GoalColliders, OutColliders;
        public Transform[] goalPoints;

        public Transform leftLimit;
        public Transform rightLimit;

        public Vector3 GetShootingVectorFromPoint (PlayerBase playerBase, 
            Transform point) {

            var playerPosition = playerBase.Position;

            var skill = playerBase.MatchPlayer.GetShooting();

            var dir = point.position - playerPosition;

            var dirErrorApplied = Ball.ApplyDirectionError(dir, skill);

            // restore by distance
            var dist = Vector3.Distance(point.position, playerPosition);
            dirErrorApplied = Vector3.Lerp(dirErrorApplied, dir, 
                EngineSettings.Current.ShootErrorRemoveByDistance.Evaluate(dist));
            // 

            var errorAppliedAngle = Mathf.Abs(Vector3.SignedAngle(dir, dirErrorApplied, Vector3.up));

            //normalize it.
            dirErrorApplied = dirErrorApplied.normalized;

            var dir2D = dirErrorApplied;
            dir2D.y = 0;

            var dirUp = dirErrorApplied;
            dirUp.x = dirUp.z = 0;

            // add multipliers.
            dirErrorApplied += dir2D * EngineSettings.Current.ShootingForwardAxisMultiplier;
            //

            dirErrorApplied *= EngineSettings.Current.ShootPowerByDistanceCurve.Evaluate(dir.magnitude);

            dirErrorApplied *= EngineSettings.Current.ShootPowerBySkillCurve.
                Evaluate(playerBase.MatchPlayer.GetShooting() / 100f);

            Debug.Log($"[Shootpoint found] {dirErrorApplied}");

            dirErrorApplied += Vector3.up * dir.magnitude * EngineSettings.Current.ShootingUpAxisDistanceMultiplier;

            Debug.Log($"[Shooting point y fixed] {dirErrorApplied}");

            Debug.DrawRay(playerPosition, dir, Color.yellow, 1);
            Debug.DrawRay(playerPosition, dirErrorApplied, Color.green, 1);

            if (dirErrorApplied.y < 1) {
                dirErrorApplied.y = 1;
            }

            return dirErrorApplied;
        }

        /// <summary>
        /// Checks all goal points, 
        /// and return shooting velocities with direction error applied.
        /// </summary>
        /// <param name="playerBase">Shooter</param>
        /// <param name="colliders">Possible colliders</param>
        /// <returns>Velocity, and applied error.</returns>
        public (Transform shootPoint, float angleFree)
            GetShootingVector (PlayerBase playerBase, PlayerBase[] colliders) {
            
            if (goalPoints.Length == 0) {
                return default;
            }

            var fieldSizeY = MatchManager.Current.SizeOfField.y;

            var mPosition = playerBase.Position;

            float minAngle (Transform m_point) {
                var pointToPlayer = m_point.position - mPosition;

                float min = colliders.Select(x => Mathf.Min (Mathf.Abs (Vector3.SignedAngle(x.Position - mPosition, pointToPlayer, Vector3.up)), 45)).
                OrderBy (x=>x).FirstOrDefault ();
                return min;
            }

            var shootingVector =
                goalPoints.Select (x=>(x, minAngle (x))).OrderBy(x => 
                 Random.Range (-5, 5) +
                 Mathf.Abs(x.x.position.x - fieldSizeY / 2) + 
                 Random.Range (0, x.x.position.y) + 
                 (45-x.Item2)/2).
                 FirstOrDefault();

            return shootingVector;
        }

        /// <summary>
        /// Middle point of the goal net.
        /// </summary>
        public Vector3 Position => middlePoint.position;

        public float GroundAnchorOffsetY {
            get {
                if (GoalColliders != null) {
                    return Mathf.Max(0f, -GoalColliders.transform.localPosition.y);
                }

                if (OutColliders != null) {
                    return Mathf.Max(0f, -OutColliders.transform.localPosition.y);
                }

                return Mathf.Max(0f, transform.position.y);
            }
        }

        public Vector3 GroundAnchorPosition =>
            new Vector3(transform.position.x, transform.position.y - GroundAnchorOffsetY, transform.position.z);

        /// <summary>
        /// Direction of the goal net. System will use this direction for attacking & defending.
        /// </summary>
        public Vector3 Direction => middlePoint.forward;

        public void AlignToPitch(Vector3 goalLineCenter, float grassY, Quaternion rotation) {
            var targetPosition = new Vector3(
                goalLineCenter.x,
                grassY + GroundAnchorOffsetY,
                goalLineCenter.z);
            transform.SetPositionAndRotation(targetPosition, rotation);
        }

        public float ResolveRequiredInfieldInset(Vector3 inwardDirection, float grassMargin = 0.18f) {
            inwardDirection = Vector3.ProjectOnPlane(inwardDirection, Vector3.up);
            if (inwardDirection.sqrMagnitude <= 0.0001f) {
                inwardDirection = transform.forward;
                inwardDirection.y = 0f;
            }

            if (inwardDirection.sqrMagnitude <= 0.0001f) {
                inwardDirection = Vector3.right;
            }

            inwardDirection.Normalize();

            var anchor = GroundAnchorPosition;
            var outsideExtent = 0f;
            var hasBounds = false;

            void AccumulateBounds(Bounds bounds) {
                var centerOffset = bounds.center - anchor;
                centerOffset.y = 0f;
                var planarExtents = new Vector3(bounds.extents.x, 0f, bounds.extents.z);
                var supportRadius =
                    Mathf.Abs(inwardDirection.x) * planarExtents.x +
                    Mathf.Abs(inwardDirection.z) * planarExtents.z;
                var projectedCenter = Vector3.Dot(centerOffset, inwardDirection);
                outsideExtent = Mathf.Max(outsideExtent, supportRadius - projectedCenter);
                hasBounds = true;
            }

            var renderers = GetComponentsInChildren<Renderer>(true);
            foreach (var renderer in renderers) {
                if (renderer == null || !renderer.enabled) {
                    continue;
                }

                AccumulateBounds(renderer.bounds);
            }

            var colliders = GetComponentsInChildren<Collider>(true);
            foreach (var collider in colliders) {
                if (collider == null || !collider.enabled) {
                    continue;
                }

                AccumulateBounds(collider.bounds);
            }

            if (!hasBounds) {
                return Mathf.Max(0.18f, grassMargin);
            }

            return Mathf.Max(0.18f, outsideExtent + Mathf.Max(0.08f, grassMargin));
        }
    }
}
