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
  readyState: number = 0; // 0 = CONNECTING, 1 = OPEN, 2 = CLOSING, 3 = CLOSED
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

  // Test Harness Component
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

  it("initiates connection to canonical spectator websocket URL", () => {
    act(() => {
      root.render(
        <StreamConsumer
          options={{
            matchId: "match-test-99",
            wsUrl: "ws://localhost:8000/ws/spectate/match-test-99",
          }}
        />
      );
    });

    expect(MockWebSocket.instances.length).toBe(1);
    const mockSocket = MockWebSocket.instances[0];
    expect(mockSocket.url).toBe("ws://localhost:8000/ws/spectate/match-test-99");
    expect(latestResult?.connectionStatus).toBe("connecting");

    // Simulate open
    act(() => {
      mockSocket.triggerOpen();
    });

    expect(latestResult?.connectionStatus).toBe("connected");
  });

  it("handles incoming snapshot and updates spectator viewer count and score", () => {
    const onViewerCountUpdate = jest.fn();
    const onScoreUpdate = jest.fn();

    act(() => {
      root.render(
        <StreamConsumer
          options={{
            matchId: "match-100",
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

    // Send snapshot event
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

  it("ingests frames through deduplicator and suppresses duplicate frames", () => {
    const onFrameReceived = jest.fn();

    act(() => {
      root.render(
        <StreamConsumer
          options={{
            matchId: "match-101",
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

    // First arrival
    act(() => {
      mockSocket.triggerMessage({
        type: "frame",
        match_id: "match-101",
        payload: { frame: frameData },
      });
    });

    expect(onFrameReceived).toHaveBeenCalledTimes(1);
    expect(latestResult?.lastFrame?.frame_id).toBe("frame-seq-1");

    // Duplicate arrival of same frame_id
    act(() => {
      mockSocket.triggerMessage({
        type: "frame",
        match_id: "match-101",
        payload: { frame: frameData },
      });
    });

    // Should still be called only once
    expect(onFrameReceived).toHaveBeenCalledTimes(1);
  });

  it("sends non-mutating client reaction and chat messages", () => {
    act(() => {
      root.render(
        <StreamConsumer
          options={{
            matchId: "match-102",
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

  it("requests resynchronization callback on connection recovery", () => {
    const onResyncRequired = jest.fn();

    act(() => {
      root.render(
        <StreamConsumer
          options={{
            matchId: "match-103",
            wsUrl: "ws://localhost:8000/ws/spectate/match-103",
            onResyncRequired,
          }}
        />
      );
    });

    const firstSocket = MockWebSocket.instances[0];
    act(() => {
      firstSocket.triggerOpen();
    });

    // Simulate drop
    act(() => {
      firstSocket.close();
    });

    expect(latestResult?.connectionStatus).toBe("reconnecting");

    // Manually trigger reconnect or trigger second socket
    act(() => {
      latestResult?.reconnect();
    });

    const secondSocket = MockWebSocket.instances[1];
    expect(secondSocket).toBeDefined();

    act(() => {
      secondSocket.triggerOpen();
    });

    expect(latestResult?.connectionStatus).toBe("connected");
    expect(onResyncRequired).toHaveBeenCalledTimes(1);
  });
});
