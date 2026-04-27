using System.Collections.Generic;
using UnityEngine;

namespace FStudio.GTEX.VisualBridge
{
    public sealed class GtexOriginalFallbackFollowCamera : MonoBehaviour
    {
        [SerializeField] private Transform ball;
        [SerializeField] private Vector3 offset = new Vector3(0f, 38f, -42f);
        [SerializeField] private float smooth = 5f;

        private readonly List<Transform> players = new List<Transform>();

        public string ModeName => "FallbackFollow";

        public bool HasValidFocus
        {
            get
            {
                if (ball != null)
                {
                    return true;
                }

                for (var index = 0; index < players.Count; index += 1)
                {
                    if (players[index] != null)
                    {
                        return true;
                    }
                }

                return false;
            }
        }

        public void Bind(Transform ballTransform, IEnumerable<Transform> playerTransforms)
        {
            ball = ballTransform;
            players.Clear();

            if (playerTransforms == null)
            {
                return;
            }

            foreach (var player in playerTransforms)
            {
                if (player != null)
                {
                    players.Add(player);
                }
            }
        }

        private void LateUpdate()
        {
            var focus = ResolveFocus();
            transform.position = Vector3.Lerp(
                transform.position,
                focus + offset,
                Time.deltaTime * smooth);

            var lookDirection = focus - transform.position;
            if (lookDirection.sqrMagnitude > 0.001f)
            {
                transform.rotation = Quaternion.LookRotation(lookDirection.normalized, Vector3.up);
            }
        }

        private Vector3 ResolveFocus()
        {
            if (ball != null)
            {
                return ball.position;
            }

            Vector3 sum = Vector3.zero;
            var count = 0;
            for (var index = 0; index < players.Count; index += 1)
            {
                if (players[index] == null)
                {
                    continue;
                }

                sum += players[index].position;
                count += 1;
            }

            return count > 0 ? sum / count : Vector3.zero;
        }
    }
}
