
using FStudio.MatchEngine.Balls;
using FStudio.Utilities;
using System;
using System.Threading.Tasks;
using UnityEngine;

namespace FStudio.MatchEngine.Graphics.GraphicsModes {
    public class BallLoader : ScriptableObject {
        private GameObject activeBall;
        private int activeBallType;

        [SerializeField] private SerializableAssetCollection<int, GameObject> balls;

        public async Task LoadBall (int ballType, Transform holder) {
            if (holder == null) {
                throw new InvalidOperationException("[BallLoader] Cannot instantiate a ball without a holder transform.");
            }

            activeBallType = ballType;
            activeBall = await balls.Instantiate(ballType, holder);
        }


        public void UnloadBall() {
            if (activeBall != null) {
                balls.ReleaseInstantiated(activeBallType, activeBall);
            }
        }

        public async Task LoadRandomBall() {
            var max = balls != null && balls.Entries != null ? balls.Entries.Length : 0;
            if (max <= 0) {
                throw new InvalidOperationException("[BallLoader] No ball prefabs are configured.");
            }

            if (Ball.Current == null || Ball.Current.ballAssetPoint == null) {
                throw new InvalidOperationException("[BallLoader] Ball.Current or its asset holder is unavailable after match creation.");
            }

            int randomBall = UnityEngine.Random.Range(0, max);
            await LoadBall(randomBall, Ball.Current.ballAssetPoint);
        }
    }
}
