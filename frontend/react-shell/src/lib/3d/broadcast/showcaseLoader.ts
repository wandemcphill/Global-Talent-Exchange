/**
 * GTEX Living Football Ecosystem — Showcase Fixture Loader Boundary (Milestone 1 Clean)
 * In Milestone 1, showcase prototypes are decoupled and return null without requiring Milestone 2 files.
 */
import type { SpectatorSafeMatchView } from "./spectatorContract";

export async function loadFiveMinuteShowcaseFixture(
  _durationSeconds: number = 300
): Promise<SpectatorSafeMatchView | null> {
  return null;
}
