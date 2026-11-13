import React, { act } from "react";
import { createRoot, type Root } from "react-dom/client";

import { OrthographicPitch } from "./OrthographicPitch";
import * as matchRenderer from "./createMatchRenderer";

const mockRender = jest.fn();
const mockDispose = jest.fn();

describe("OrthographicPitch lifecycle", () => {
  let root: Root;
  let host: HTMLDivElement;

  beforeEach(() => {
    (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
    mockDispose.mockClear();
    mockRender.mockClear();
    jest.spyOn(matchRenderer, "createMatchRenderer").mockReturnValue({
      setSize: jest.fn(),
      setPixelRatio: jest.fn(),
      render: mockRender,
      dispose: mockDispose,
      domElement: document.createElement("canvas"),
      info: { render: { calls: 0 } },
    } as unknown as ReturnType<typeof matchRenderer.createMatchRenderer>);
    host = document.createElement("div");
    document.body.appendChild(host);
    root = createRoot(host);
  });

  afterEach(() => {
    jest.restoreAllMocks();
    host.remove();
  });

  test("creates one renderer and disposes it", () => {
    const players = Array.from({ length: 22 }, (_, index) => ({
      playerId: `p-${index}`,
      side: index < 11 ? ("home" as const) : ("away" as const),
      x: (index % 11) / 11,
      y: index < 11 ? 0.3 : 0.7,
      shirtNumber: (index % 11) + 1,
      name: `P${index}`,
    }));
    act(() => {
      root.render(
        <OrthographicPitch players={players} ball={{ x: 0.5, y: 0.5 }} eventType="pass" />,
      );
    });
    expect(mockRender).toHaveBeenCalled();
    act(() => root.unmount());
    expect(mockDispose).toHaveBeenCalled();
  });

  test("does not import pixi and exports a memoized pitch", () => {
    const source = require("fs").readFileSync(require("path").join(__dirname, "OrthographicPitch.tsx"), "utf8");
    expect(source).not.toMatch(/pixi/i);
    expect(source).toContain("memo(OrthographicPitchComponent)");
    expect(source).toContain("webglcontextrestored");
  });
});
