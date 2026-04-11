using UnityEngine;

#if UNITY_EDITOR
using UnityEditor;
#endif

namespace FStudio.MatchEngine.Players.PlayerController
{
    public partial class CodeBasedController
    {
#if UNITY_EDITOR
        protected virtual void OnDrawGizmos()
        {
            // Safety first – avoid editor crashes
            if (!debugger || !Application.isPlaying)
                return;

            if (BasePlayer == null)
                return;

            Vector3 pos = transform.position;
            pos.y += 0.1f;

            //-----------------------------------
            // PLAYER BASE DISC
            //-----------------------------------
            Gizmos.color = Color.yellow;
            Gizmos.DrawWireSphere(pos, 0.6f);

            //-----------------------------------
            // MOVEMENT DIRECTION
            //-----------------------------------
            if (Direction != Vector3.zero)
            {
                Gizmos.color = Color.cyan;
                Gizmos.DrawLine(pos, pos + Direction.normalized * 3f);

#if UNITY_EDITOR
                Handles.Label(pos + Direction.normalized * 3.2f, "Move Dir");
#endif
            }

            //-----------------------------------
            // TARGET POSITION
            //-----------------------------------
            Gizmos.color = Color.magenta;
            Gizmos.DrawSphere(targetPosition, 0.3f);

#if UNITY_EDITOR
            Handles.Label(targetPosition + Vector3.up * 0.5f, "Target");
#endif

            //-----------------------------------
            // FORWARD DIRECTION
            //-----------------------------------
            Gizmos.color = Color.green;
            Gizmos.DrawLine(pos, pos + transform.forward * 2f);

            //-----------------------------------
            // TEXT INFO BLOCK
            //-----------------------------------
#if UNITY_EDITOR
            float yOffset = 1.5f;

            if (BasePlayer.MatchPlayer?.Player != null)
            {
                Handles.Label(pos + Vector3.up * yOffset,
                    $"Name: {BasePlayer.MatchPlayer.Player.Name}");
                yOffset += 0.5f;
            }

            Handles.Label(pos + Vector3.up * yOffset,
                $"Speed: {MoveSpeed:F2} / {TargetMoveSpeed:F2}");
            yOffset += 0.5f;

            Handles.Label(pos + Vector3.up * yOffset,
                $"Has Ball: {BasePlayer.IsHoldingBall}");
            yOffset += 0.5f;

            Handles.Label(pos + Vector3.up * yOffset,
                $"Act: {BasePlayer.CurrentAct}");
            yOffset += 0.5f;

            //-----------------------------------
            // OFFSIDE WARNING
            //-----------------------------------
            if (BasePlayer.IsInOffside)
            {
                Handles.color = Color.red;
                Handles.Label(pos + Vector3.up * (yOffset + 0.3f), "OFFSIDE");
            }

            //-----------------------------------
            // MARKERS (SAFE)
            //-----------------------------------
            if (BasePlayer.Markers != null && BasePlayer.Markers.Members != null)
            {
                string markers = "";
                foreach (var marker in BasePlayer.Markers.Members)
                {
                    if (marker?.MatchPlayer?.Player != null)
                        markers += marker.MatchPlayer.Player.Name + ", ";
                }

                if (!string.IsNullOrEmpty(markers))
                {
                    Handles.color = Color.white;
                    Handles.Label(pos + Vector3.up * (yOffset + 0.8f),
                        $"Markers: {markers}");
                }
            }
#endif

            //-----------------------------------
            // NEAREST PLAYER LINE (NO TEAM ASSUMPTIONS)
            //-----------------------------------
            var players = Object.FindObjectsByType<CodeBasedController>(FindObjectsSortMode.None);

            CodeBasedController closest = null;
            float minDist = float.MaxValue;

            foreach (var p in players)
            {
                if (p == this || p == null)
                    continue;

                float dist = Vector3.Distance(pos, p.transform.position);
                if (dist < minDist)
                {
                    minDist = dist;
                    closest = p;
                }
            }

            if (closest != null)
            {
                Gizmos.color = Color.blue;
                Gizmos.DrawLine(pos, closest.transform.position);

#if UNITY_EDITOR
                Handles.Label((pos + closest.transform.position) / 2f,
                    $"Nearest: {minDist:F1}m");
#endif
            }

            //-----------------------------------
            // BALL LINE (SAFE)
            //-----------------------------------
            if (FStudio.MatchEngine.Balls.Ball.Current != null)
            {
                Gizmos.color = Color.white;
                Gizmos.DrawLine(pos, FStudio.MatchEngine.Balls.Ball.Current.transform.position);
            }
        }
#endif
    }
}