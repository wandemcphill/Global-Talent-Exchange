import React, { act } from "react";
import { createRoot, Root } from "react-dom/client";
import {
  useMatchSpectatorStream,
  UseMatchSpectatorStreamOptions,
  UseMatchSpectatorStreamResult,
} from "./useMatchSpectatorStream";

// Mock WebSocket implementation for stream testing
class MockWebSocket {
  static instances: MockWebSocket[] = [];
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  url: string;
  readyState: number = 0;
  onopen: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: ((err: any) => void) | null = null;
  sentMessages: string[] = [];

  constructor(url: string) {
    this.url = url;
    this.readyState = 0;
    MockWebSocket.instances.push(this);
  }

  send(data: string) {
    this.sentMessages.push(data);
  }

  close() {
    this.readyState = 3;
    if (this.onclose) {
      this.onclose();
    }
  }

  triggerOpen() {
    this.readyState = 1;
    if (this.onopen) {
      this.onopen();
    }
  }

  triggerMessage(data: any) {
    if (this.onmessage) {
      this.onmessage({ data: typeof data === "string" ? data : JSON.stringify(data) });
    }
  }
}

describe("useMatchSpectatorStream", () => {
  let container: HTMLDivElement;
  let root: Root;
  const originalWebSocket = global.WebSocket;

  beforeEach(() => {
    (global as any).IS_REACT_ACT_ENVIRONMENT = true;
    MockWebSocket.instances = [];
    (global as any).WebSocket = MockWebSocket as any;
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => {
      root.unmount();
    });
    container.remove();
    (global as any).WebSocket = originalWebSocket;
  });

  let latestResult: UseMatchSpectatorStreamResult | null = null;

  function StreamConsumer({ options }: { options: UseMatchSpectatorStreamOptions }) {
    const result = useMatchSpectatorStream(options);
    latestResult = result;
    return (
      <div data-testid="status" data-status={result.connectionStatus}>
        {result.connectionStatus}
      </div>
    );
  }

  it("allows guest spectators to connect without requiring authentication tickets", async () => {
    await act(async () => {
      root.render(
        <StreamConsumer
          options={{
            matchId: "match-guest-99",
            isAuthenticated: false,
            wsUrl: "ws://localhost:8000/ws/spectate/match-guest-99",
          }}
        />
      );
    });

    expect(MockWebSocket.instances.length).toBe(1);
    const mockSocket = MockWebSocket.instances[0];
    expect(mockSocket.url).toBe("ws://localhost:8000/ws/spectate/match-guest-99");
    expect(mockSocket.url).not.toContain("ticket=");
    expect(latestResult?.connectionStatus).toBe("connecting");

    act(() => {
      mockSocket.triggerOpen();
    });

    expect(latestResult?.connectionStatus).toBe("connected");
  });

  it("handles incoming snapshot and updates spectator viewer count and score", async () => {
    const onViewerCountUpdate = jest.fn();
    const onScoreUpdate = jest.fn();

    await act(async () => {
      root.render(
        <StreamConsumer
          options={{
            matchId: "match-100",
            isAuthenticated: false,
            wsUrl: "ws://localhost:8000/ws/spectate/match-100",
            onViewerCountUpdate,
            onScoreUpdate,
          }}
        />
      );
    });

    const mockSocket = MockWebSocket.instances[0];
    act(() => {
      mockSocket.triggerOpen();
    });

    act(() => {
      mockSocket.triggerMessage({
        type: "snapshot",
        match_id: "match-100",
        snapshot: {
          viewer_count: 1420,
          score_update: {
            match_id: "match-100",
            score: "2 - 1",
            home_score: 2,
            away_score: 1,
            minute: 68,
          },
        },
      });
    });

    expect(latestResult?.viewerCount).toBe(1420);
    expect(onViewerCountUpdate).toHaveBeenCalledWith(1420);
    expect(latestResult?.latestScore).toEqual({
      home_score: 2,
      away_score: 1,
      minute: 68,
      status: undefined,
    });
    expect(onScoreUpdate).toHaveBeenCalledWith({
      home_score: 2,
      away_score: 1,
      minute: 68,
      status: undefined,
    });
  });

  it("ingests frames through deduplicator and suppresses duplicate frames", async () => {
    const onFrameReceived = jest.fn();

    await act(async () => {
      root.render(
        <StreamConsumer
          options={{
            matchId: "match-101",
            isAuthenticated: false,
            wsUrl: "ws://localhost:8000/ws/spectate/match-101",
            onFrameReceived,
          }}
        />
      );
    });

    const mockSocket = MockWebSocket.instances[0];
    act(() => {
      mockSocket.triggerOpen();
    });

    const frameData = {
      frame_id: "frame-seq-1",
      time_seconds: 12.5,
      clock_minute: 0,
      phase: "open_play",
      home_score: 0,
      away_score: 0,
      home_attacks_right: true,
      possession_side: "home",
      camera_preset: "broadcast",
      players: [],
      ball: { position: { x: 50, y: 50 }, height: 0, state: "rolling" },
    };

    act(() => {
      mockSocket.triggerMessage({
        type: "frame",
        match_id: "match-101",
        payload: { frame: frameData },
      });
    });

    expect(onFrameReceived).toHaveBeenCalledTimes(1);
    expect(latestResult?.lastFrame?.frame_id).toBe("frame-seq-1");

    act(() => {
      mockSocket.triggerMessage({
        type: "frame",
        match_id: "match-101",
        payload: { frame: frameData },
      });
    });

    expect(onFrameReceived).toHaveBeenCalledTimes(1);
  });

  it("sends non-mutating client reaction and chat messages", async () => {
    await act(async () => {
      root.render(
        <StreamConsumer
          options={{
            matchId: "match-102",
            isAuthenticated: false,
            wsUrl: "ws://localhost:8000/ws/spectate/match-102",
          }}
        />
      );
    });

    const mockSocket = MockWebSocket.instances[0];
    act(() => {
      mockSocket.triggerOpen();
    });

    act(() => {
      latestResult?.sendReaction("🔥");
      latestResult?.sendChatMessage("What a strike!");
    });

    expect(mockSocket.sentMessages.length).toBe(2);
    expect(JSON.parse(mockSocket.sentMessages[0])).toEqual({
      type: "reaction",
      reaction: "🔥",
    });
    expect(JSON.parse(mockSocket.sentMessages[1])).toEqual({
      type: "chat_message",
      message: "What a strike!",
    });
  });

  it("requests a fresh single-use ticket on initial connection and obtains a new ticket on reconnect", async () => {
    const onResyncRequired = jest.fn();
    let ticketCounter = 0;
    const requestTicket = jest.fn(async (targetMatchId: string) => {
      ticketCounter += 1;
      return `single_use_ticket_${targetMatchId}_${ticketCounter}`;
    });

    await act(async () => {
      root.render(
        <StreamConsumer
          options={{
            matchId: "match-auth-103",
            isAuthenticated: true,
            requestTicket,
            wsUrl: "ws://localhost:8000/ws/spectate/match-auth-103?TOKEN=leaked-jwt&Access_Token=leaked2",
            onResyncRequired,
          }}
        />
      );
    });

    expect(requestTicket).toHaveBeenCalledTimes(1);
    expect(requestTicket).toHaveBeenCalledWith("match-auth-103");
    expect(MockWebSocket.instances.length).toBe(1);

    const firstSocket = MockWebSocket.instances[0];
    expect(firstSocket.url).toContain("ticket=single_use_ticket_match-auth-103_1");
    expect(firstSocket.url.toLowerCase()).not.toContain("token=");
    expect(firstSocket.url.toLowerCase()).not.toContain("access_token=");
    expect(firstSocket.url).not.toContain("leaked-jwt");

    act(() => {
      firstSocket.triggerOpen();
    });
    expect(latestResult?.connectionStatus).toBe("connected");

    // Simulate connection drop and manual reconnect
    act(() => {
      firstSocket.close();
    });
    expect(latestResult?.connectionStatus).toBe("reconnecting");

    await act(async () => {
      latestResult?.reconnect();
    });

    expect(requestTicket).toHaveBeenCalledTimes(2);
    expect(MockWebSocket.instances.length).toBe(2);
    const secondSocket = MockWebSocket.instances[1];
    expect(secondSocket.url).toContain("ticket=single_use_ticket_match-auth-103_2");
    expect(secondSocket.url).not.toContain("single_use_ticket_match-auth-103_1");

    act(() => {
      secondSocket.triggerOpen();
    });

    expect(latestResult?.connectionStatus).toBe("connected");
    expect(onResyncRequired).toHaveBeenCalledTimes(1);
  });

  it("does not silently downgrade to guest connection when authenticated ticket issuance fails or replays", async () => {
    const failingRequestTicket = jest.fn(async () => {
      throw new Error("Ticket issuance endpoint 401/503");
    });

    await act(async () => {
      root.render(
        <StreamConsumer
          options={{
            matchId: "match-auth-fail-1",
            isAuthenticated: true,
            requestTicket: failingRequestTicket,
            wsUrl: "ws://localhost:8000/ws/spectate/match-auth-fail-1",
          }}
        />
      );
    });

    expect(failingRequestTicket).toHaveBeenCalledTimes(1);
    expect(MockWebSocket.instances.length).toBe(0);
    expect(latestResult?.connectionStatus).toBe("error");
  });

  it("prevents concurrent reconnect calls from racing while a ticket request is in flight", async () => {
    let resolveTicket: ((val: string) => void) | null = null;
    const slowRequestTicket = jest.fn(
      () =>
        new Promise<string>((resolve) => {
          resolveTicket = resolve;
        })
    );

    await act(async () => {
      root.render(
        <StreamConsumer
          options={{
            matchId: "match-race-1",
            isAuthenticated: true,
            requestTicket: slowRequestTicket,
            wsUrl: "ws://localhost:8000/ws/spectate/match-race-1",
          }}
        />
      );
    });

    expect(slowRequestTicket).toHaveBeenCalledTimes(1);

    // Trigger multiple reconnects while first ticket request is still in flight
    act(() => {
      latestResult?.reconnect();
      latestResult?.reconnect();
    });

    // Must not fire duplicate concurrent ticket requests
    expect(slowRequestTicket).toHaveBeenCalledTimes(1);

    await act(async () => {
      if (resolveTicket) {
        resolveTicket("atomic_ticket_1");
      }
    });

    expect(MockWebSocket.instances.length).toBe(1);
    expect(MockWebSocket.instances[0].url).toContain("ticket=atomic_ticket_1");
  });


  it("discards stale ticket responses if disconnect occurs or a newer connection starts before ticket resolution", async () => {
    let resolveFirstTicket: ((val: string) => void) | null = null;
    let resolveSecondTicket: ((val: string) => void) | null = null;
    let callCount = 0;

    const requestTicket = jest.fn(() => {
      callCount += 1;
      const count = callCount;
      return new Promise<string>((resolve) => {
        if (count === 1) {
          resolveFirstTicket = resolve;
        } else {
          resolveSecondTicket = resolve;
        }
      });
    });

    await act(async () => {
      root.render(
        <StreamConsumer
          options={{
            matchId: "match-stale-race-1",
            isAuthenticated: true,
            requestTicket,
            wsUrl: "ws://localhost:8000/ws/spectate/match-stale-race-1",
          }}
        />
      );
    });

    expect(requestTicket).toHaveBeenCalledTimes(1);
    expect(latestResult?.connectionStatus).toBe("connecting");

    // User calls disconnect while ticket 1 is in-flight
    act(() => {
      latestResult?.disconnect();
    });
    expect(latestResult?.connectionStatus).toBe("disconnected");

    // Stale ticket 1 resolves AFTER disconnect
    await act(async () => {
      if (resolveFirstTicket) {
        resolveFirstTicket("stale_ticket_1");
      }
    });

    // Stale ticket 1 resolution must NOT open a WebSocket or change status away from disconnected
    expect(MockWebSocket.instances.length).toBe(0);
    expect(latestResult?.connectionStatus).toBe("disconnected");

    // Now user reconnects, starting operation 2
    await act(async () => {
      latestResult?.reconnect();
    });
    expect(requestTicket).toHaveBeenCalledTimes(2);

    // Ticket 2 resolves
    await act(async () => {
      if (resolveSecondTicket) {
        resolveSecondTicket("valid_ticket_2");
      }
    });

    // Only ticket 2 opens a WebSocket
    expect(MockWebSocket.instances.length).toBe(1);
    expect(MockWebSocket.instances[0].url).toContain("ticket=valid_ticket_2");
    expect(MockWebSocket.instances[0].url).not.toContain("stale_ticket_1");
  });
});