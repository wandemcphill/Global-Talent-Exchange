declare const describe: any;
declare const it: any;
declare const expect: any;
declare const beforeEach: any;
declare const afterEach: any;
declare const jest: any;

import React, { act } from "react";
import { createRoot, Root } from "react-dom/client";
import AuthPage from "./AuthPage";

var mockNavigate = jest.fn();
var mockSetSearchParams = jest.fn();
var mockSearchParams = new URLSearchParams();
var mockUser: any = null;
var mockAuthLoading = false;
var mockLogin = jest.fn();
var mockSignup = jest.fn();
var mockToastError = jest.fn();
var mockTurnstileSiteKey = "";

jest.mock("react-router-dom", () => ({
  Link: ({ to, children, ...rest }: any) => <a href={to} {...rest}>{children}</a>,
  useNavigate: () => mockNavigate,
  useSearchParams: () => [mockSearchParams, mockSetSearchParams],
}));
jest.mock("@/lib/auth", () => ({
  useAuth: () => ({ user: mockUser, loading: mockAuthLoading, login: mockLogin, signup: mockSignup }),
}));
jest.mock("sonner", () => ({ toast: { error: (...args: any[]) => mockToastError(...args), success: jest.fn() } }));
jest.mock("@/components/advertising/GtexAdvertising", () => ({
  GtexAuthAdvertisingPanel: () => <div data-testid="auth-ad-panel" />,
}));
jest.mock("@/components/gtex/TurnstileChallenge", () => ({
  get TURNSTILE_SITE_KEY() { return mockTurnstileSiteKey; },
  TurnstileChallenge: ({ onTokenChange }: any) => (
    <div data-testid="mock-turnstile">
      <button type="button" data-testid="simulate-turnstile-success" onClick={() => onTokenChange("cf-turnstile-verified-token")}>
        Complete Security Check
      </button>
    </div>
  ),
}));

function setInput(element: HTMLInputElement | HTMLSelectElement, value: string) {
  const prototype = element instanceof HTMLSelectElement ? window.HTMLSelectElement.prototype : window.HTMLInputElement.prototype;
  const setter = Object.getOwnPropertyDescriptor(prototype, "value")?.set;
  if (setter) setter.call(element, value);
  else element.value = value;
  element.dispatchEvent(new Event("input", { bubbles: true }));
  element.dispatchEvent(new Event("change", { bubbles: true }));
}

function clickCheckbox(element: HTMLInputElement) {
  element.click();
}

describe("GTEX role-specific signup contracts", () => {
  let container: HTMLDivElement | null = null;
  let root: Root | null = null;

  beforeEach(() => {
    (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    mockNavigate.mockReset();
    mockSetSearchParams.mockReset();
    mockLogin.mockReset();
    mockSignup.mockReset();
    mockToastError.mockReset();
    mockUser = null;
    mockAuthLoading = false;
    mockSearchParams = new URLSearchParams();
    mockTurnstileSiteKey = "";
    Object.defineProperty(window.crypto, "subtle", {
      configurable: true,
      value: {
        importKey: jest.fn().mockResolvedValue({}),
        deriveBits: jest.fn().mockResolvedValue(new Uint8Array(32).buffer),
      },
    });
  });

  afterEach(() => {
    if (root) act(() => root?.unmount());
    if (container?.parentNode) container.parentNode.removeChild(container);
    container = null;
    root = null;
  });

  it("renders standard user signup fields and submits only the user schema fields", async () => {
    mockSignup.mockResolvedValueOnce({ user: { id: "user-1", account_type: "user" } });
    act(() => root?.render(<AuthPage mode="signup" />));

    setInput(container?.querySelector('[data-testid="signup-fullname-input"]') as HTMLInputElement, "Jane Doe");
    setInput(container?.querySelector('[data-testid="signup-username-input"]') as HTMLInputElement, "jane_doe");
    setInput(container?.querySelector('[data-testid="signup-email-input"]') as HTMLInputElement, "jane@example.com");
    setInput(container?.querySelector('[data-testid="signup-password-input"]') as HTMLInputElement, "ValidPassword123!");
    act(() => {
      clickCheckbox(container?.querySelector('[data-testid="signup-over18-checkbox"]') as HTMLInputElement);
      clickCheckbox(container?.querySelector('[data-testid="signup-terms-checkbox"]') as HTMLInputElement);
    });

    await act(async () => {
      (container?.querySelector('[data-testid="signup-form"]') as HTMLFormElement).dispatchEvent(
        new Event("submit", { bubbles: true, cancelable: true }),
      );
    });

    expect(mockSignup).toHaveBeenCalledWith(expect.objectContaining({
      account_type: "user",
      full_name: "Jane Doe",
      username: "jane_doe",
      email: "jane@example.com",
      is_over_18: true,
    }));
    expect(mockSignup.mock.calls[0][0]).not.toHaveProperty("trading_alias");
    expect(mockSignup.mock.calls[0][0]).not.toHaveProperty("creator_name");
    expect(mockNavigate).toHaveBeenCalledWith("/app");
  });

  it("submits Creator signup using the dedicated Creator schema", async () => {
    mockSignup.mockResolvedValueOnce({ user: { id: "creator-1", account_type: "creator" } });
    act(() => root?.render(<AuthPage mode="signup" />));
    setInput(container?.querySelector('[data-testid="signup-account-type"]') as HTMLSelectElement, "creator");
    setInput(container?.querySelector('[data-testid="creator-name-input"]') as HTMLInputElement, "Jane Sports Media");
    setInput(container?.querySelector('[data-testid="creator-username-input"]') as HTMLInputElement, "janesports");
    setInput(container?.querySelector('[data-testid="creator-country-input"]') as HTMLInputElement, "Nigeria");
    setInput(container?.querySelector('[data-testid="creator-category-input"]') as HTMLSelectElement, "sports");
    setInput(container?.querySelector('[data-testid="creator-language-input"]') as HTMLInputElement, "English");
    setInput(container?.querySelector('[data-testid="signup-email-input"]') as HTMLInputElement, "jane@example.com");
    setInput(container?.querySelector('[data-testid="signup-password-input"]') as HTMLInputElement, "ValidPassword123!");
    act(() => clickCheckbox(container?.querySelector('[data-testid="signup-terms-checkbox"]') as HTMLInputElement));

    await act(async () => {
      (container?.querySelector('[data-testid="signup-form"]') as HTMLFormElement).dispatchEvent(
        new Event("submit", { bubbles: true, cancelable: true }),
      );
    });

    expect(mockSignup).toHaveBeenCalledWith(expect.objectContaining({
      account_type: "creator",
      creator_name: "Jane Sports Media",
      username: "janesports",
      country: "Nigeria",
      category: "sports",
      primary_language: "English",
      email: "jane@example.com",
    }));
    expect(mockSignup.mock.calls[0][0]).not.toHaveProperty("full_name");
    expect(mockSignup.mock.calls[0][0]).not.toHaveProperty("is_over_18");
    expect(mockSignup.mock.calls[0][0]).not.toHaveProperty("trading_alias");
    expect(mockNavigate).toHaveBeenCalledWith("/app/creator-access");
  });

  it("submits Coin Trader signup using its full schema with no generic username or age flag", async () => {
    mockSignup.mockResolvedValueOnce({ user: { id: "trader-1", account_type: "coin_trader" } });
    act(() => root?.render(<AuthPage mode="signup" />));
    setInput(container?.querySelector('[data-testid="signup-account-type"]') as HTMLSelectElement, "coin_trader");
    setInput(container?.querySelector('[data-testid="trader-fullname-input"]') as HTMLInputElement, "Ade Ola");
    setInput(container?.querySelector('[data-testid="trader-alias-input"]') as HTMLInputElement, "AdeFX");
    setInput(container?.querySelector('[data-testid="trader-phone-input"]') as HTMLInputElement, "+2348012345678");
    setInput(container?.querySelector('[data-testid="trader-country-input"]') as HTMLInputElement, "Nigeria");
    setInput(container?.querySelector('[data-testid="trader-currency-input"]') as HTMLSelectElement, "NGN");
    setInput(container?.querySelector('[data-testid="trader-experience-input"]') as HTMLSelectElement, "beginner");
    setInput(container?.querySelector('[data-testid="trader-totp-code-input"]') as HTMLInputElement, "123456");
    setInput(container?.querySelector('[data-testid="trader-recovery-input"]') as HTMLInputElement, "alpha bravo charlie delta echo foxtrot golf hotel india juliet");
    setInput(container?.querySelector('[data-testid="trader-pin-input"]') as HTMLInputElement, "123456");
    setInput(container?.querySelector('[data-testid="signup-email-input"]') as HTMLInputElement, "ade@example.com");
    setInput(container?.querySelector('[data-testid="signup-password-input"]') as HTMLInputElement, "ValidPassword123!");
    act(() => clickCheckbox(container?.querySelector('[data-testid="signup-terms-checkbox"]') as HTMLInputElement));

    await act(async () => {
      (container?.querySelector('[data-testid="signup-form"]') as HTMLFormElement).dispatchEvent(
        new Event("submit", { bubbles: true, cancelable: true }),
      );
    });

    const payload = mockSignup.mock.calls[0][0];
    expect(payload).toEqual(expect.objectContaining({
      account_type: "coin_trader",
      full_name: "Ade Ola",
      trading_alias: "AdeFX",
      phone_number: "+2348012345678",
      country: "Nigeria",
      preferred_currency: "NGN",
      trading_experience: "beginner",
      totp_code: "123456",
    }));
    expect(payload.totp_secret).toMatch(/^[A-Z2-7]{32}$/);
    expect(payload.recovery_phrase_hash).toMatch(/^pbkdf2-sha256\$/);
    expect(payload.security_pin_hash).toMatch(/^pbkdf2-sha256\$/);
    expect(payload).not.toHaveProperty("username");
    expect(payload).not.toHaveProperty("is_over_18");
    expect(payload).not.toHaveProperty("recovery_phrase");
    expect(payload).not.toHaveProperty("security_pin");
    expect(mockNavigate).toHaveBeenCalledWith("/app/coin-traders");
  });

  it("blocks submission until the required account terms and age conditions are met", async () => {
    act(() => root?.render(<AuthPage mode="signup" />));
    await act(async () => {
      (container?.querySelector('[data-testid="signup-form"]') as HTMLFormElement).dispatchEvent(
        new Event("submit", { bubbles: true, cancelable: true }),
      );
    });
    expect(mockSignup).not.toHaveBeenCalled();
    expect(mockToastError).toHaveBeenCalledWith("Accept the GTEX terms to continue.");
  });

  it("requires Turnstile when the site key is configured", async () => {
    mockTurnstileSiteKey = "test-site-key";
    act(() => root?.render(<AuthPage mode="signup" />));
    setInput(container?.querySelector('[data-testid="signup-fullname-input"]') as HTMLInputElement, "Test User");
    setInput(container?.querySelector('[data-testid="signup-username-input"]') as HTMLInputElement, "test_user");
    setInput(container?.querySelector('[data-testid="signup-email-input"]') as HTMLInputElement, "test@example.com");
    setInput(container?.querySelector('[data-testid="signup-password-input"]') as HTMLInputElement, "ValidPassword123!");
    act(() => {
      clickCheckbox(container?.querySelector('[data-testid="signup-over18-checkbox"]') as HTMLInputElement);
      clickCheckbox(container?.querySelector('[data-testid="signup-terms-checkbox"]') as HTMLInputElement);
    });
    const form = container?.querySelector('[data-testid="signup-form"]') as HTMLFormElement;
    await act(async () => form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })));
    expect(mockSignup).not.toHaveBeenCalled();
    expect(mockToastError).toHaveBeenCalledWith("Complete the security check to continue.");

    act(() => (container?.querySelector('[data-testid="simulate-turnstile-success"]') as HTMLButtonElement).click());
    await act(async () => form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })));
    expect(mockSignup).toHaveBeenCalledWith(expect.objectContaining({ turnstile_token: "cf-turnstile-verified-token" }));
  });

  it("keeps login mode compatible", async () => {
    mockLogin.mockResolvedValueOnce({ user: { id: "user-2", account_type: "user" }, landingRoute: "/app" });
    act(() => root?.render(<AuthPage mode="login" />));
    setInput(container?.querySelector('[data-testid="login-email-input"]') as HTMLInputElement, "user@example.com");
    setInput(container?.querySelector('[data-testid="login-password-input"]') as HTMLInputElement, "Password123");
    await act(async () => {
      (container?.querySelector('[data-testid="login-form"]') as HTMLFormElement).dispatchEvent(
        new Event("submit", { bubbles: true, cancelable: true }),
      );
    });
    expect(mockLogin).toHaveBeenCalledWith("user@example.com", "Password123");
    expect(mockNavigate).toHaveBeenCalledWith("/app");
  });
});
