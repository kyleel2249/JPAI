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
    expect(within(screen.getByRole("navigation")).getByRole("button", { name: "◈ Intelligence" })).toBeTruthy();
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

  it("opens the quality governance workspace", () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ status: "ok", service: "JPAI", environment: "test", mode: "local-first" }),
    }));
    render(<App />);
    fireEvent.click(within(screen.getByRole("navigation")).getByRole("button", { name: /Quality & Improvement/ }));
    expect(screen.getByRole("heading", { name: /continuous improvement control/i })).toBeTruthy();
    expect(screen.getByRole("heading", { name: /assess → find cause → fix → test → verify/i })).toBeTruthy();
    expect(screen.getByRole("heading", { name: /issue resolution register/i })).toBeTruthy();
  });
  it("opens the web intelligence crawler workspace", () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ({ status: "available", items: [], pages_stored: 0, domains_indexed: 0, jobs_total: 0 }) }));
    render(<App />);
    fireEvent.click(within(screen.getByRole("navigation")).getByRole("button", { name: /Web Intelligence/ }));
    expect(screen.getByRole("heading", { name: /discovery, crawling & extraction/i })).toBeTruthy();
    expect(screen.getByRole("heading", { name: /launch a governed crawl/i })).toBeTruthy();
  });
});
