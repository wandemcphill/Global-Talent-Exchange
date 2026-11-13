import fs from "fs";
import path from "path";

test("the match page stacks score, pitch, commentary, then tactics below 768px", () => {
  const source = fs.readFileSync(path.join(__dirname, "../MatchCenter.tsx"), "utf8");
  expect(source).toContain("max-md:flex max-md:flex-col");
  expect(source).toContain("order-1");
  expect(source).toContain("order-2");
  expect(source).toContain("order-3");
  expect(source).toContain("order-4");
  const pitch = source.indexOf("order-2 space-y-4 max-md:block");
  const commentary = source.indexOf("order-3 max-md:block");
  const tactics = source.indexOf("order-4 max-md:block");
  expect(pitch).toBeGreaterThan(0);
  expect(commentary).toBeGreaterThan(pitch);
  expect(tactics).toBeGreaterThan(pitch);
});
