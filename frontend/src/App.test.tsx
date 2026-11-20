// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import App from "./App";

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe("JPAI command centre", () => {
  it("renders the product identity and institutional overview", () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ status: "ok", service: "JPAI", environment: "test", mode: "local-first" }),
    }));
    render(<App />);
    expect(screen.getByRole("heading", { name: /intelligence, orchestrated\./i })).toBeTruthy();
    expect(screen.getByRole("heading", { name: /operational overview/i })).toBeTruthy();
    expect(within(screen.getByRole("navigation")).getByRole("button", { name: /Intelligence/ })).toBeTruthy();
  });

  it("opens the persistent memory workspace", () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ status: "ok", service: "JPAI", environment: "test", mode: "local-first" }),
    }));
    render(<App />);
    fireEvent.click(within(screen.getByRole("navigation")).getByRole("button", { name: /Memory/ }));
    expect(screen.getByRole("heading", { name: /memory & knowledge/i })).toBeTruthy();
    expect(screen.getByText(/capture a memory/i)).toBeTruthy();
  });
});
