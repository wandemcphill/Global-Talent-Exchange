declare const describe: any;
declare const it: any;
declare const expect: any;
declare const beforeEach: any;
declare const afterEach: any;
declare const jest: any;

import React, { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import AuthPage from "./AuthPage";

var mockNavigate = jest.fn();
var mockSearchParams = new URLSearchParams();
var mockSetSearchParams = jest.fn();
var mockUser: any = null;
var mockAuthLoading = false;
var mockLogin = jest.fn();
var mockSignup = jest.fn();
var mockToastError = jest.fn();
var mockToastSuccess = jest.fn();
var mockTurnstileSiteKey = "";

jest.mock("react-router-dom", () => ({
  Link: ({ to, children, ...rest }: any) => <a href={to} {...rest}>{children}</a>,
  useNavigate: () => mockNavigate,
  useSearchParams: () => [mockSearchParams, mockSetSearchParams],
}));

jest.mock("@/lib/auth", () => ({
  useAuth: () => ({ user: mockUser, loading: mockAuthLoading, login: mockLogin, signup: mockSignup }),
}));

jest.mock("sonner", () => ({
  toast: {
    error: (...args: any[]) => mockToastError(...args),
    success: (...args: any[]) => mockToastSuccess(...args),
  },
}));

jest.mock("@/components/advertising/GtexAdvertising", () => ({
  GtexAuthAdvertisingPanel: () => <div data-testid="auth-ad-panel" />,
}));

jest.mock("@/components/gtex/TurnstileChallenge", () => ({
  get TURNSTILE_SITE_KEY() { return mockTurnstileSiteKey; },
  TurnstileChallenge: ({ onTokenChange }: any) => (
    <div data-testid="mock-turnstile">
      <button type="button" data-testid="simulate-turnstile-success" onClick={() => onTokenChange("verified-turnstile-token")}>
        Complete Security Check
      </button>
    </div>
  ),
}));

function setInput(element: HTMLInputElement | HTMLSelectElement, value: string) {
  act(() => {
    const prototype = element instanceof HTMLSelectElement ? window.HTMLSelectElement.prototype : window.HTMLInputElement.prototype;
    const setter = Object.getOwnPropertyDescriptor(prototype, "value")?.set;
    if (setter) setter.call(element, value);
    else element.value = value;
    element.dispatchEvent(new Event("input", { bubbles: true }));
    element.dispatchEvent(new Event("change", { bubbles: true }));
  });
}

function clickCheckbox(element: HTMLInputElement) {
  element.click();
}

function selectTrader(container: HTMLDivElement) {
  setInput(container.querySelector('[data-testid="signup-account-type"]') as HTMLSelectElement, "coin_trader");
}

function fillTraderBasics(container: HTMLDivElement) {
  setInput(container.querySelector('[data-testid="trader-fullname-input"]') as HTMLInputElement, "Ade Ola");
  setInput(container.querySelector('[data-testid="trader-alias-input"]') as HTMLInputElement, "AdeFX");
  setInput(container.querySelector('[data-testid="trader-phone-input"]') as HTMLInputElement, "+2348012345678");
  setInput(container.querySelector('[data-testid="trader-country-input"]') as HTMLInputElement, "Nigeria");
  setInput(container.querySelector('[data-testid="trader-currency-input"]') as HTMLSelectElement, "NGN");
  setInput(container.querySelector('[data-testid="trader-experience-input"]') as HTMLSelectElement, "beginner");
  setInput(container.querySelector('[data-testid="trader-wallet-label-input"]') as HTMLInputElement, "Lagos Main Desk");
  setInput(container.querySelector('[data-testid="trader-totp-code-input"]') as HTMLInputElement, "123456");
  setInput(container.querySelector('[data-testid="signup-email-input"]') as HTMLInputElement, "ade@example.com");
  setInput(container.querySelector('[data-testid="signup-password-input"]') as HTMLInputElement, "ValidPassword123!");
  clickCheckbox(container.querySelector('[data-testid="signup-terms-checkbox"]') as HTMLInputElement);
}

describe("GTEX signup and trader authenticator flow", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    mockNavigate.mockReset();
    mockLogin.mockReset();
    mockSignup.mockReset();
    mockToastError.mockReset();
    mockToastSuccess.mockReset();
    mockUser = null;
    mockAuthLoading = false;
    mockSearchParams = new URLSearchParams();
    mockTurnstileSiteKey = "";
    const signature = new Uint8Array(20);
    signature[1] = 0x01;
    signature[2] = 0xe2;
    signature[3] = 0x40;
    Object.defineProperty(window, "crypto", {
      configurable: true,
      value: {
        getRandomValues: (arr: Uint8Array) => {
          for (let i = 0; i < arr.length; i += 1) arr[i] = (i * 19 + 7) & 0xff;
          return arr;
        },
        subtle: {
          importKey: jest.fn().mockResolvedValue({}),
          sign: jest.fn().mockResolvedValue(signature.buffer),
        },
      },
    });
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
  });

  it("shows the three personal account types as visible choices", () => {
    act(() => root.render(<AuthPage mode="signup" />));
    expect(container.querySelector('[data-testid="signup-account-type-user"]')).not.toBeNull();
    expect(container.querySelector('[data-testid="signup-account-type-coin_trader"]')).not.toBeNull();
    expect(container.querySelector('[data-testid="signup-account-type-creator"]')).not.toBeNull();
    expect(container.querySelector('[data-testid="signup-account-type-options"]')?.textContent).toContain("Coin Trader");
  });

  it("submits a Coin Trader account after a valid six-digit TOTP check without extra phrase or PIN", async () => {
    mockSignup.mockResolvedValueOnce({ user: { id: "trader-1", account_type: "coin_trader" } });
    act(() => root.render(<AuthPage mode="signup" />));
    selectTrader(container);
    fillTraderBasics(container);

    await act(async () => {
      (container.querySelector('[data-testid="trader-verify-totp-button"]') as HTMLButtonElement).click();
    });
    expect(container.querySelector('[data-testid="trader-verify-totp-button"]')?.textContent).toContain("Authenticator verified");

    await act(async () => {
      (container.querySelector('[data-testid="signup-form"]') as HTMLFormElement).dispatchEvent(
        new Event("submit", { bubbles: true, cancelable: true }),
      );
    });

    const payload = mockSignup.mock.calls[0][0];
    expect(payload).toEqual(expect.objectContaining({
      account_type: "coin_trader",
      full_name: "Ade Ola",
      trading_alias: "AdeFX",
      totp_code: "123456",
    }));
    expect(payload).not.toHaveProperty("recovery_phrase_hash");
    expect(payload).not.toHaveProperty("security_pin_hash");
    expect(payload).not.toHaveProperty("recovery_phrase");
    expect(payload).not.toHaveProperty("security_pin");
    expect(mockNavigate).toHaveBeenCalledWith("/app/coin-traders");
  });

  it("does not submit a trader signup until the authenticator has been verified", async () => {
    act(() => root.render(<AuthPage mode="signup" />));
    selectTrader(container);
    fillTraderBasics(container);
    await act(async () => {
      (container.querySelector('[data-testid="signup-form"]') as HTMLFormElement).dispatchEvent(
        new Event("submit", { bubbles: true, cancelable: true }),
      );
    });
    expect(mockSignup).not.toHaveBeenCalled();
    expect(container.textContent).toContain("Verify your authenticator code before creating your account.");
  });

  it("clears a stale top-level error when the user edits a field", async () => {
    act(() => root.render(<AuthPage mode="signup" />));
    const form = container.querySelector('[data-testid="signup-form"]') as HTMLFormElement;
    await act(async () => form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })));
    expect(container.querySelector('[data-testid="auth-form-error"]')?.textContent).toContain("Accept the GTEX terms");
    setInput(container.querySelector('[data-testid="signup-email-input"]') as HTMLInputElement, "new@example.com");
    expect(container.querySelector('[data-testid="auth-form-error"]')).toBeNull();
  });

  it("requires Turnstile only when a site key is configured", async () => {
    mockTurnstileSiteKey = "test-site-key";
    act(() => root.render(<AuthPage mode="signup" />));
    setInput(container.querySelector('[data-testid="signup-fullname-input"]') as HTMLInputElement, "Test User");
    setInput(container.querySelector('[data-testid="signup-username-input"]') as HTMLInputElement, "test_user");
    setInput(container.querySelector('[data-testid="signup-email-input"]') as HTMLInputElement, "test@example.com");
    setInput(container.querySelector('[data-testid="signup-password-input"]') as HTMLInputElement, "ValidPassword123!");
    clickCheckbox(container.querySelector('[data-testid="signup-over18-checkbox"]') as HTMLInputElement);
    clickCheckbox(container.querySelector('[data-testid="signup-terms-checkbox"]') as HTMLInputElement);
    const form = container.querySelector('[data-testid="signup-form"]') as HTMLFormElement;
    await act(async () => form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })));
    expect(mockSignup).not.toHaveBeenCalled();
    expect(mockToastError).toHaveBeenCalledWith("Complete the security check to continue.");
    act(() => (container.querySelector('[data-testid="simulate-turnstile-success"]') as HTMLButtonElement).click());
    await act(async () => form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })));
    expect(mockSignup).toHaveBeenCalledWith(expect.objectContaining({ turnstile_token: "verified-turnstile-token" }));
  });

  it("keeps login mode compatible", async () => {
    mockLogin.mockResolvedValueOnce({ user: { id: "user-2", account_type: "user" }, landingRoute: "/app" });
    act(() => root.render(<AuthPage mode="login" />));
    setInput(container.querySelector('[data-testid="login-email-input"]') as HTMLInputElement, "user@example.com");
    setInput(container.querySelector('[data-testid="login-password-input"]') as HTMLInputElement, "Password123");
    await act(async () => {
      (container.querySelector('[data-testid="login-form"]') as HTMLFormElement).dispatchEvent(
        new Event("submit", { bubbles: true, cancelable: true }),
      );
    });
    expect(mockLogin).toHaveBeenCalledWith("user@example.com", "Password123");
    expect(mockNavigate).toHaveBeenCalledWith("/app");
  });
});
