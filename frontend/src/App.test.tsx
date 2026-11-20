// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import App from "./App";

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe("JPAI application shell", () => {
  it("renders the product identity and local-first capabilities", () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ({ status: "ok", service: "JPAI", environment: "test", mode: "local-first" }) }));
    render(<App />);
    expect(screen.getByRole("heading", { name: /intelligence, orchestrated\./i })).toBeTruthy();
    expect(screen.getByText(/local-first core/i)).toBeTruthy();
  });
});
