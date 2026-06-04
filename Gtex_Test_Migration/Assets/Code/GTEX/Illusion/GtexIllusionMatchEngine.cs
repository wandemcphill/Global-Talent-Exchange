using System.Collections.Generic;

namespace FStudio.GTEX.Illusion
{
    public static class GtexIllusionMatchEngine
    {
        public static GtexIllusionTimeline GenerateDefaultTimeline(
            int seed,
            string homeTeam,
            string awayTeam)
        {
            var rng = new GtexIllusionRandom(seed);
            var events = new List<GtexIllusionTimelineEvent>();

            events.Add(Create(0f, "commentary", "home", commentary: "Kickoff. GTEX illusion playback is live."));
            events.Add(Create(3f, "pass", "home", "home-6", "home-8", commentary: "Home settle into a short passing rhythm."));
            events.Add(Create(7f, "pass", "home", "home-8", "home-10", commentary: "The ball is worked into the left half-space."));
            events.Add(Create(11f, "dribble", "home", "home-10", duration: 1.35f, x: 21f, z: 19f, commentary: "Home carry forward, waiting for the striker to move."));
            events.Add(Create(15f, "through_pass", "home", "home-10", "home-9", duration: 1.25f, commentary: "A measured through pass splits the defensive line."));

            var firstShotGoal = rng.Chance(0.28f);
            events.Add(Create(18f, "shot", "home", player: "home-9", duration: 1.15f, outcome: firstShotGoal ? "goal" : "save", commentary: "The striker gets the shot away."));
            events.Add(firstShotGoal
                ? Create(19f, "goal", "home", player: "home-9", commentary: "Goal. Home convert the first big chance.")
                : Create(19f, "save", "away", player: "away-1", commentary: "The keeper reads it and gathers cleanly."));

            events.Add(Create(28f, "pass", "away", "away-4", "away-6", commentary: "Away rebuild from the back instead of clearing long."));
            events.Add(Create(35f, "tackle", "home", player: "home-5", target: "away-10", commentary: "Home step in early and halt the counter."));
            events.Add(Create(44f, "pass", "home", "home-7", "home-11", commentary: "Home switch play before half-time."));
            events.Add(Create(48f, "pass", "home", "home-11", "home-9", commentary: "A low pass finds feet at the edge of the area."));

            var secondShotGoal = rng.Chance(0.58f);
            events.Add(Create(51f, "shot", "home", player: "home-9", duration: 1.2f, outcome: secondShotGoal ? "goal" : "save", commentary: "Home shoot from a cleaner angle."));
            events.Add(secondShotGoal
                ? Create(52f, "goal", "home", player: "home-9", commentary: "Goal. The move gets the finish it deserved.")
                : Create(52f, "save", "away", player: "away-1", commentary: "Another save keeps away alive."));

            events.Add(Create(66f, "foul", "away", player: "away-5", target: "home-10", commentary: "Away break up the next attack with a foul."));
            events.Add(Create(74f, "through_pass", "away", "away-8", "away-9", duration: 1.25f, commentary: "Away finally find space behind the home defence."));
            events.Add(Create(77f, "shot", "away", player: "away-9", duration: 1.1f, outcome: rng.Chance(0.22f) ? "goal" : "save", commentary: "Away test the keeper from a narrow lane."));
            events.Add(Create(78f, "save", "home", player: "home-1", commentary: "The home keeper holds position and makes the save."));
            events.Add(Create(90f, "commentary", "home", commentary: "Full time. Phase 1 playback complete."));

            return new GtexIllusionTimeline
            {
                matchId = "illusion-seeded-" + seed,
                homeTeam = string.IsNullOrWhiteSpace(homeTeam) ? "Kano Pillars" : homeTeam.Trim(),
                awayTeam = string.IsNullOrWhiteSpace(awayTeam) ? "Enyimba FC" : awayTeam.Trim(),
                seed = seed,
                events = events.ToArray()
            };
        }

        private static GtexIllusionTimelineEvent Create(
            float minute,
            string type,
            string team,
            string from = "",
            string to = "",
            string player = "",
            string target = "",
            string outcome = "",
            string commentary = "",
            string overlay = "",
            float duration = 0f,
            float x = 0f,
            float z = 0f)
        {
            return new GtexIllusionTimelineEvent
            {
                minute = minute,
                type = type,
                team = team,
                from = from,
                to = to,
                player = player,
                target = target,
                outcome = outcome,
                commentary = commentary,
                overlay = overlay,
                duration = duration,
                x = x,
                z = z
            };
        }

        private struct GtexIllusionRandom
        {
            private uint state;

            public GtexIllusionRandom(int seed)
            {
                state = seed == 0 ? 0x6D2B79F5u : unchecked((uint)seed);
            }

            public bool Chance(float probability)
            {
                return Next01() <= probability;
            }

            private float Next01()
            {
                state += 0x6D2B79F5u;
                var value = state;
                value = (value ^ (value >> 15)) * (value | 1u);
                value ^= value + ((value ^ (value >> 7)) * (value | 61u));
                return ((value ^ (value >> 14)) & 0x00FFFFFFu) / 16777216f;
            }
        }
    }
}
