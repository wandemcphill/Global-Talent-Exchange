import { bindWebGLContextRestoration, createFrameScheduler } from "./GtexWebGLHost";

describe("GtexWebGLHost", () => {
  test("frame scheduler stops when the tick asks it to stop", () => {
    const frames: number[] = [];
    let queued: FrameRequestCallback | null = null;
    const original = global.requestAnimationFrame;
    (global as any).requestAnimationFrame = (cb: FrameRequestCallback) => {
      queued = cb;
      return 1;
    };
    (global as any).cancelAnimationFrame = () => {
      queued = null;
    };
    try {
      const scheduler = createFrameScheduler(1000, () => {
        frames.push(1);
        return false;
      });
      scheduler.start();
      queued?.(0);
      queued?.(20);
      queued?.(40);
      expect(frames.length).toBe(1);
    } finally {
      global.requestAnimationFrame = original;
    }
  });

  test("context loss is preventDefaulted and restoration is reported", () => {
    const canvas = document.createElement("canvas");
    const events: string[] = [];
    const stop = bindWebGLContextRestoration(canvas, {
      onLost: () => events.push("lost"),
      onRestored: () => events.push("restored"),
    });
    const lost = new Event("webglcontextlost", { cancelable: true });
    canvas.dispatchEvent(lost);
    expect(lost.defaultPrevented).toBe(true);
    canvas.dispatchEvent(new Event("webglcontextrestored"));
    expect(events).toEqual(["lost", "restored"]);
    stop();
    canvas.dispatchEvent(new Event("webglcontextrestored"));
    expect(events).toEqual(["lost", "restored"]);
  });

  test("stopping the scheduler cancels the animation frame", () => {
    const cancelled: number[] = [];
    const originalRaf = global.requestAnimationFrame;
    const originalCancel = global.cancelAnimationFrame;
    (global as any).requestAnimationFrame = () => 7;
    (global as any).cancelAnimationFrame = (id: number) => cancelled.push(id);
    try {
      const scheduler = createFrameScheduler(30, () => true);
      scheduler.start();
      scheduler.stop();
      expect(cancelled).toContain(7);
    } finally {
      global.requestAnimationFrame = originalRaf;
      global.cancelAnimationFrame = originalCancel;
    }
  });
});
