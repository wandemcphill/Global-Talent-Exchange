using FStudio.MatchEngine.Events;
using FStudio.UI.Events;
using UnityEngine;
using FStudio.Loaders;
using System.Threading.Tasks;
using UnityEngine.AddressableAssets;
using FStudio.Events;
using Shared.Responses;
using FStudio.UI.Graphics;
using UnityEngine.UI;
using FStudio.UI.MatchThemes.MatchEvents;
using FStudio.Database;

namespace FStudio.UI.MatchThemes {
    public class BigScorePanel : ScoreboardPanel {
        private const int MAX_GOAL_PER_TEAM = 50;
        
        private bool isInitialized;
        private bool isDestroyed;
        //InfoboardEvent
        private StaticPool<ScoreboardScorerMember, PlayerEntry> homeScorersPool, awayScorersPool;

        [SerializeField] private Transform homeScorerHolder, awayScorerHolder;

        [SerializeField] private AssetReference scorerElementAsset;

        [SerializeField] private Image homeTeamLogo;
        [SerializeField] private Image awayTeamLogo;

        private bool CanUsePanel => !isDestroyed && this != null && gameObject != null;

        private async Task<StaticPool<ScoreboardScorerMember, PlayerEntry>> InitScorerBoard (Transform scorerHolder) {
            var scorerPool = new StaticPool<ScoreboardScorerMember, PlayerEntry>(scorerElementAsset, scorerHolder);

            if (!CanUsePanel || scorerHolder == null || scorerElementAsset == null || !scorerElementAsset.RuntimeKeyIsValid()) {
                Debug.LogWarning("[BigScorePanel] Skipping scorer board initialization because the panel, holder, or asset reference is unavailable.");
                return scorerPool;
            }

            for (int i = 0; i < MAX_GOAL_PER_TEAM; i++) {
                if (!CanUsePanel || scorerHolder == null) {
                    break;
                }

                var asset = scorerElementAsset.InstantiateAsync(scorerHolder).Task;
                await asset;

                if (!CanUsePanel || scorerHolder == null) {
                    if (asset.Result != null) {
                        Destroy(asset.Result);
                    }
                    break;
                }

                var instance = asset.Result;
                if (instance == null) {
                    continue;
                }

                instance.SetActive(false); // hide.

                var member = instance.GetComponent<ScoreboardScorerMember>();
                if (member == null) {
                    Debug.LogWarning("[BigScorePanel] Scorer element is missing ScoreboardScorerMember. Destroying pooled instance.");
                    Destroy(instance);
                    continue;
                }

                scorerPool.Add(member);
            }

            return scorerPool;
        }

        protected override void OnEnable() {
            base.OnEnable();

            EventManager.Subscribe<GoalScoredEvent>(OnGoalScored);
            EventManager.Subscribe<InfoboardEvent>(OnInfoBoard);
            EventManager.Subscribe<UpcomingMatchEvent>(UpcomingMatch);
            EventManager.Subscribe<KickOffEvent>(Kickoff);
        }

        protected override void OnDisable() {
            base.OnDisable();

            EventManager.UnSubscribe<GoalScoredEvent>(OnGoalScored);
            EventManager.UnSubscribe<InfoboardEvent>(OnInfoBoard);
            EventManager.UnSubscribe<UpcomingMatchEvent>(UpcomingMatch);
            EventManager.UnSubscribe<KickOffEvent>(Kickoff);
        }

        private void OnDestroy() {
            isDestroyed = true;
        }

        protected override void OnEventCalled (UpcomingMatchEvent upcomingMatchEvent) {
            if (!CanUsePanel || upcomingMatchEvent == null) {
                return;
            }

            base.OnEventCalled(upcomingMatchEvent);

            var logoMaterial = GetLogo(upcomingMatchEvent.details.homeTeam.TeamLogo);
            if (homeTeamLogo != null) {
                homeTeamLogo.material = logoMaterial;
            }

            logoMaterial = GetLogo(upcomingMatchEvent.details.awayTeam.TeamLogo);
            if (awayTeamLogo != null) {
                awayTeamLogo.material = logoMaterial;
            }

            // clear scores.
            void clear(StaticPool<ScoreboardScorerMember, PlayerEntry> pool) {
                if (pool == null) {
                    return;
                }

                foreach (var e in pool.Members) {
                    if (e != null) {
                        e.IsActive = false;
                    }
                }
            }

            if (!isInitialized) {
                return;
            }

            clear(homeScorersPool);
            clear(awayScorersPool);
        }

        private async void OnGoalScored (GoalScoredEvent goalScored) {
            if (!CanUsePanel || !isInitialized) {
                return;
            }

            var targetPool = !goalScored.Side ? homeScorersPool : awayScorersPool;
            if (targetPool == null) {
                return;
            }

            var member = targetPool.Get();
            if (member == null) {
                return;
            }

            await member.SetMember(goalScored.Scorer);
            if (!CanUsePanel || member == null) {
                return;
            }

            member.SetMinute(goalScored.Minute);

            member.IsActive = true;
        }

        private async Task Initialize () {
            if (isInitialized || !CanUsePanel) {
                return;
            }

            homeScorersPool = await InitScorerBoard(homeScorerHolder);
            awayScorersPool = await InitScorerBoard(awayScorerHolder);

            if (!CanUsePanel) {
                return;
            }

            isInitialized = true;
        }

        private void Clear () {
            void clear(StaticPool<ScoreboardScorerMember, PlayerEntry> pool) {
                if (pool == null) {
                    return;
                }

                foreach (var e in pool.Members) {
                    if (e != null) {
                        e.MarkAsDeactive();
                    }
                }
            }

            if (isInitialized) {
                clear(homeScorersPool);
                clear(awayScorersPool);
            }
        }

        private async void UpcomingMatch (UpcomingMatchEvent eventObject) {
            if (!CanUsePanel || eventObject == null) {
                return;
            }

            await Initialize();
        }

        private async void Kickoff (KickOffEvent eventObject) {
            if (!CanUsePanel) {
                return;
            }

            Appear();

            await Task.Delay(3000);

            if (!CanUsePanel) {
                return;
            }

            Disappear();
        }

        private void OnInfoBoard (InfoboardEvent eventObject) {
            if (eventObject == null) {
                Clear();
                Disappear();
            } else {
                async void enabler(StaticPool<ScoreboardScorerMember, PlayerEntry> pool) {
                    if (pool == null) {
                        return;
                    }

                    foreach (var e in pool.Members) {
                        if (!CanUsePanel) {
                            return;
                        }

                        if (e != null && e.IsActive) {
                            await Task.Delay(200);
                            if (!CanUsePanel || e == null) {
                                return;
                            }
                            e.MarkAsActive();
                        }
                    }
                }

                enabler(homeScorersPool);
                enabler(awayScorersPool);

                Appear();
            }
        }

        private Material GetLogo(LogoEntry logo) {
            var result = TeamLogoMaterial.Current.GetColoredMaterial(logo);
            return result;
        }
    }
}
