import React, { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { PrematchClassicFlow } from "./PrematchClassicFlow";

describe("PrematchClassicFlow", () => {
  let host: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
    host = document.createElement("div");
    document.body.appendChild(host);
    root = createRoot(host);
  });

  afterEach(() => {
    act(() => root.unmount());
    host.remove();
  });

  test("shows the filed roster, a team talk, and the competition table", () => {
    const kickOff = jest.fn();
    act(() => {
      root.render(
        <PrematchClassicFlow
          homeName="Coventry"
          awayName="Nottingham Forest"
          competitionName="Premier League"
          refereeName="Tom Bramall"
          homePlayers={[
            { player_id: "1", player_name: "Carl Rushworth", shirt_number: 1, role: "GK", line: "goalkeeper" },
            { player_id: "3", player_name: "Callum Doyle", shirt_number: 3, role: "CB", line: "defense" },
            { player_id: "11", player_name: "Liel Abada", shirt_number: 11, role: "ST", line: "attack", mood: "Composed" },
          ]}
          awayPlayers={[{ player_id: "9", player_name: "Morgan Gibbs-White", shirt_number: 10, role: "AM", line: "attack" }]}
          coachNotes={["Go out there and make it count."]}
          standings={[
            { team_name: "Coventry", position: 20, played: 5, goal_difference: -6, points: 2 },
            { team_name: "Nottingham Forest", position: 12, played: 5, goal_difference: 2, points: 7 },
          ]}
          onKickOff={kickOff}
        />,
      );
    });

    expect(host.querySelector("[data-testid='prematch-official-roster']")?.textContent).toContain("Carl Rushworth");
    expect(host.textContent).toContain("Tom Bramall");
    expect(host.textContent).not.toContain("Joe Edwards");

    act(() => {
      (host.querySelector("[data-testid='prematch-view-talk']") as HTMLButtonElement).click();
    });
    expect(host.textContent).toContain("Go out there and make it count.");
    expect(host.textContent).toContain("Liel Abada");
    expect(host.textContent).toContain("Composed");
    act(() => {
      (host.querySelector("[data-testid='prematch-send-talk']") as HTMLButtonElement).click();
    });
    expect(host.textContent).toContain("Addressed the room.");

    act(() => {
      (host.querySelector("[data-testid='prematch-view-table']") as HTMLButtonElement).click();
    });
    expect(host.querySelector("[data-testid='prematch-league-table']")?.textContent).toContain("Nottingham Forest");
    act(() => {
      (host.querySelector("[data-testid='prematch-kickoff']") as HTMLButtonElement).click();
    });
    expect(kickOff).toHaveBeenCalled();
  });
});
