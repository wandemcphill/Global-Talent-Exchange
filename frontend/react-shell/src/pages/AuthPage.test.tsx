declare const describe: any;
declare const it: any;
declare const test: any;
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

jest.mock("react-router-dom", () => ({
  Link: ({ to, children, ...rest }: any) => (
    <a href={to} {...rest}>
      {children}
    </a>
  ),
  useNavigate: () => mockNavigate,
  useSearchParams: () => [mockSearchParams, mockSetSearchParams],
}));

jest.mock("@/lib/auth", () => ({
  useAuth: () => ({
    user: mockUser,
    loading: mockAuthLoading,
    login: mockLogin,
    signup: mockSignup,
  }),
}));

jest.mock("sonner", () => ({
  toast: {
    error: (...args: any[]) => mockToastError(...args),
  },
}));

jest.mock("@/components/advertising/GtexAdvertising", () => ({
  GtexAuthAdvertisingPanel: () => <div data-testid="auth-ad-panel" />,
}));

var mockTurnstileSiteKey = "";

jest.mock("@/components/gtex/TurnstileChallenge", () => ({
  get TURNSTILE_SITE_KEY() {
    return mockTurnstileSiteKey;
  },
  TurnstileChallenge: ({ onTokenChange }: any) => (
    <div data-testid="mock-turnstile">
      <button
        type="button"
        data-testid="simulate-turnstile-success"
        onClick={() => onTokenChange("cf-turnstile-verified-token")}
      >
        Complete Security Check
      </button>
    </div>
  ),
}));

function changeInput(input: HTMLInputElement, value: string) {
  const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value")?.set;
  if (setter) {
    setter.call(input, value);
  } else {
    input.value = value;
  }
  input.dispatchEvent(new Event("input", { bubbles: true }));
  input.dispatchEvent(new Event("change", { bubbles: true }));
}

function checkCheckbox(checkbox: HTMLInputElement, checked: boolean) {
  if (checkbox.checked !== checked) {
    checkbox.click();
  }
}

describe("Unified AuthPage Onboarding & Login (Issue #228)", () => {
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
  });

  afterEach(() => {
    if (root) {
      act(() => {
        root?.unmount();
      });
    }
    if (container && container.parentNode) {
      container.parentNode.removeChild(container);
    }
    container = null;
    root = null;
  });

  it("renders a unified signup form without segregated account-type selector or client-side TOTP UI", () => {
    act(() => {
      root?.render(<AuthPage mode="signup" />);
    });

    // Unified fields must be present
    expect(container?.querySelector('[data-testid="signup-fullname-input"]')).not.toBeNull();
    expect(container?.querySelector('[data-testid="signup-username-input"]')).not.toBeNull();
    expect(container?.querySelector('[data-testid="signup-email-input"]')).not.toBeNull();
    expect(container?.querySelector('[data-testid="signup-password-input"]')).not.toBeNull();
    expect(container?.querySelector('[data-testid="signup-over18-checkbox"]')).not.toBeNull();
    expect(container?.querySelector('[data-testid="signup-submit-button"]')).not.toBeNull();

    // Segregated account choice buttons must be absent
    expect(container?.querySelector('[data-testid="signup-account-user"]')).toBeNull();
    expect(container?.querySelector('[data-testid="signup-account-creator"]')).toBeNull();
    expect(container?.querySelector('[data-testid="signup-account-coin_trader"]')).toBeNull();

    // Client-side TOTP secret UI must be absent
    expect(container?.querySelector('[data-testid="signup-totp-secret"]')).toBeNull();

    // Unified account explanation notice is shown
    expect(container?.textContent).toContain("Unified GTEX Account");
    expect(container?.textContent).toContain("One account unlocks the full platform");
  });

  it("submits unified user registration payload and routes to /app by default", async () => {
    mockSignup.mockResolvedValueOnce({ user: { id: "u-123", account_type: "user" } });

    act(() => {
      root?.render(<AuthPage mode="signup" />);
    });

    const fullNameInput = container?.querySelector('[data-testid="signup-fullname-input"]') as HTMLInputElement;
    const usernameInput = container?.querySelector('[data-testid="signup-username-input"]') as HTMLInputElement;
    const emailInput = container?.querySelector('[data-testid="signup-email-input"]') as HTMLInputElement;
    const passwordInput = container?.querySelector('[data-testid="signup-password-input"]') as HTMLInputElement;
    const over18Checkbox = container?.querySelector('[data-testid="signup-over18-checkbox"]') as HTMLInputElement;
    const form = container?.querySelector('[data-testid="signup-form"]') as HTMLFormElement;

    act(() => {
      changeInput(fullNameInput, "John Doe");
      changeInput(usernameInput, "johndoe");
      changeInput(emailInput, "john@example.com");
      changeInput(passwordInput, "ValidPassword123!"); // pragma: allowlist secret
      checkCheckbox(over18Checkbox, true);
    });

    await act(async () => {
      form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    });

    expect(mockSignup).toHaveBeenCalledTimes(1);
    expect(mockSignup).toHaveBeenCalledWith({
      account_type: "user",
      full_name: "John Doe",
      username: "johndoe",
      email: "john@example.com",
      password: "ValidPassword123!", // pragma: allowlist secret
      is_over_18: true,
    });
    expect(mockNavigate).toHaveBeenCalledWith("/app");
  });

  it("prevents signup submission and displays toast error if over18 is unchecked", async () => {
    act(() => {
      root?.render(<AuthPage mode="signup" />);
    });

    const form = container?.querySelector('[data-testid="signup-form"]') as HTMLFormElement;

    await act(async () => {
      form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    });

    expect(mockSignup).not.toHaveBeenCalled();
    expect(mockToastError).toHaveBeenCalledWith("You must be 18 or older to sign up for a GTEX account.");
  });

  it("navigates to creator specialization route when ?role=creator is present on signup", async () => {
    mockSearchParams = new URLSearchParams("role=creator");
    mockSignup.mockResolvedValueOnce({ user: { id: "u-creator", account_type: "user" } });

    act(() => {
      root?.render(<AuthPage mode="signup" />);
    });

    expect(container?.textContent).toContain("Specialization intent:");
    expect(container?.textContent).toContain("creator");

    const fullNameInput = container?.querySelector('[data-testid="signup-fullname-input"]') as HTMLInputElement;
    const usernameInput = container?.querySelector('[data-testid="signup-username-input"]') as HTMLInputElement;
    const emailInput = container?.querySelector('[data-testid="signup-email-input"]') as HTMLInputElement;
    const passwordInput = container?.querySelector('[data-testid="signup-password-input"]') as HTMLInputElement;
    const over18Checkbox = container?.querySelector('[data-testid="signup-over18-checkbox"]') as HTMLInputElement;
    const form = container?.querySelector('[data-testid="signup-form"]') as HTMLFormElement;

    act(() => {
      changeInput(fullNameInput, "Creator Jane");
      changeInput(usernameInput, "creator_jane");
      changeInput(emailInput, "jane@creator.test");
      changeInput(passwordInput, "ValidPassword123!"); // pragma: allowlist secret
      checkCheckbox(over18Checkbox, true);
    });

    await act(async () => {
      form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    });

    expect(mockSignup).toHaveBeenCalledTimes(1);
    expect(mockNavigate).toHaveBeenCalledWith("/app/creator-access");
  });

  it("renders login mode cleanly and redirects upon sign-in", async () => {
    mockLogin.mockResolvedValueOnce({
      user: { id: "u-existing", account_type: "user" },
      landingRoute: "/app",
    });

    act(() => {
      root?.render(<AuthPage mode="login" />);
    });

    expect(container?.querySelector('[data-testid="login-email-input"]')).not.toBeNull();
    expect(container?.querySelector('[data-testid="login-password-input"]')).not.toBeNull();
    expect(container?.querySelector('[data-testid="signup-fullname-input"]')).toBeNull();

    const emailInput = container?.querySelector('[data-testid="login-email-input"]') as HTMLInputElement;
    const passwordInput = container?.querySelector('[data-testid="login-password-input"]') as HTMLInputElement;
    const form = container?.querySelector('[data-testid="login-form"]') as HTMLFormElement;

    act(() => {
      changeInput(emailInput, "user@test.com");
      changeInput(passwordInput, "Password123");
    });

    await act(async () => {
      form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    });

    expect(mockLogin).toHaveBeenCalledWith("user@test.com", "Password123");
    expect(mockNavigate).toHaveBeenCalledWith("/app");
  });

  it("renders signed-in state when user already has an active session visiting /signup", () => {
    mockUser = { id: "u-active", username: "active_scout", email: "scout@test.com" };

    act(() => {
      root?.render(<AuthPage mode="signup" />);
    });

    expect(container?.textContent).toContain("You are already signed in");
    expect(container?.textContent).toContain("active_scout");
    expect(container?.querySelector('[data-testid="return-to-console-link"]')).not.toBeNull();
  });

  it("enforces Turnstile challenge gating when site key is active", async () => {
    mockTurnstileSiteKey = "0x4AAAAAAA-TEST-SITE-KEY";

    act(() => {
      root?.render(<AuthPage mode="signup" />);
    });

    const fullNameInput = container?.querySelector('[data-testid="signup-fullname-input"]') as HTMLInputElement;
    const usernameInput = container?.querySelector('[data-testid="signup-username-input"]') as HTMLInputElement;
    const emailInput = container?.querySelector('[data-testid="signup-email-input"]') as HTMLInputElement;
    const passwordInput = container?.querySelector('[data-testid="signup-password-input"]') as HTMLInputElement;
    const over18Checkbox = container?.querySelector('[data-testid="signup-over18-checkbox"]') as HTMLInputElement;
    const form = container?.querySelector('[data-testid="signup-form"]') as HTMLFormElement;

    act(() => {
      changeInput(fullNameInput, "Turnstile User");
      changeInput(usernameInput, "turnstile_user");
      changeInput(emailInput, "turnstile@example.com");
      changeInput(passwordInput, "ValidPassword123!"); // pragma: allowlist secret
      checkCheckbox(over18Checkbox, true);
    });

    // 1. Submit without solving challenge -> should be blocked
    await act(async () => {
      form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    });

    expect(mockSignup).not.toHaveBeenCalled();
    expect(mockToastError).toHaveBeenCalledWith("Complete the security check to continue.");

    // 2. Solve challenge and submit -> should succeed with turnstile_token
    const solveChallengeBtn = container?.querySelector('[data-testid="simulate-turnstile-success"]') as HTMLButtonElement;
    act(() => {
      solveChallengeBtn.click();
    });

    await act(async () => {
      form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    });

    expect(mockSignup).toHaveBeenCalledTimes(1);
    expect(mockSignup).toHaveBeenCalledWith({
      account_type: "user",
      full_name: "Turnstile User",
      username: "turnstile_user",
      email: "turnstile@example.com",
      password: "ValidPassword123!", // pragma: allowlist secret
      is_over_18: true,
      turnstile_token: "cf-turnstile-verified-token",
    });
  });
});
