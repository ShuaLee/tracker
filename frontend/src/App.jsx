import { useCallback, useEffect, useState } from "react";
import { ensureCsrfCookie, fetchMe } from "./api.js";
import ForgotPasswordScreen from "./ForgotPasswordScreen.jsx";
import LoginScreen from "./LoginScreen.jsx";
import PortfolioScreen from "./PortfolioScreen.jsx";
import RegisterScreen from "./RegisterScreen.jsx";
import ResetPasswordScreen from "./ResetPasswordScreen.jsx";
import SettingsScreen from "./SettingsScreen.jsx";
import VerifyEmailScreen from "./VerifyEmailScreen.jsx";

// No router library yet - the only real URLs are the two the backend emails
// link to (accounts/emails.py). Everything else is in-memory screen state.
function readEmailLink() {
  const params = new URLSearchParams(window.location.search);
  const get = (key) => params.get(key) || "";
  switch (window.location.pathname) {
    case "/verify-email":
      return { kind: "verify", uid: get("uid"), email: get("email"), token: get("token") };
    case "/reset-password":
      return { kind: "reset", uid: get("uid"), token: get("token") };
    default:
      return null;
  }
}

export default function App() {
  const [me, setMe] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [emailLink, setEmailLink] = useState(readEmailLink);
  // Which logged-out screen: "login" | "register" | "forgot".
  const [screen, setScreen] = useState("login");
  // Which logged-in screen: "portfolio" | "settings".
  const [tab, setTab] = useState("portfolio");

  const refreshMe = useCallback(async () => {
    try {
      const response = await fetchMe();
      setMe(response.ok ? response.data : null);
      setLoadError(null);
    } catch (error) {
      // fetch() rejects on a network-level failure (backend not running,
      // CORS blocked, etc) rather than resolving with an error status -
      // without this, that left the app stuck on "Loading..." forever.
      setLoadError(error.message);
    }
  }, []);

  useEffect(() => {
    (async () => {
      try {
        await ensureCsrfCookie(); // sets the csrftoken cookie needed for login/logout/etc
      } catch (error) {
        setLoadError(error.message);
        setLoading(false);
        return;
      }
      await refreshMe();
      setLoading(false);
    })();
  }, [refreshMe]);

  // Leaving an emailed link: drop its token from the address bar and
  // re-check the session (verifying may have changed the email; a password
  // reset signs out every session, including this one).
  async function leaveEmailLink() {
    window.history.replaceState(null, "", "/");
    setEmailLink(null);
    setScreen("login");
    await refreshMe();
  }

  function handleLoggedOut() {
    setMe(null);
    setScreen("login");
    setTab("portfolio");
  }

  if (loading) return <p>Loading...</p>;

  if (loadError) {
    return (
      <div>
        <p>Couldn't reach the backend: {loadError}</p>
        <p>Is `manage.py runserver` running at the API base URL in frontend/.env?</p>
      </div>
    );
  }

  if (emailLink?.kind === "verify") {
    return <VerifyEmailScreen {...emailLink} onDone={leaveEmailLink} />;
  }
  if (emailLink?.kind === "reset") {
    return <ResetPasswordScreen {...emailLink} onDone={leaveEmailLink} />;
  }

  if (me) {
    return (
      <div>
        <nav>
          <button type="button" onClick={() => setTab("portfolio")} disabled={tab === "portfolio"}>
            Portfolio
          </button>{" "}
          <button type="button" onClick={() => setTab("settings")} disabled={tab === "settings"}>
            Settings
          </button>{" "}
          <span>Signed in as {me.email}</span>
        </nav>
        {tab === "portfolio" ? (
          <PortfolioScreen />
        ) : (
          <SettingsScreen me={me} onUpdated={setMe} onLoggedOut={handleLoggedOut} />
        )}
      </div>
    );
  }

  if (screen === "register") {
    return <RegisterScreen onBackToLogin={() => setScreen("login")} />;
  }
  if (screen === "forgot") {
    return <ForgotPasswordScreen onBackToLogin={() => setScreen("login")} />;
  }
  return (
    <LoginScreen
      onLoggedIn={setMe}
      onCreateAccount={() => setScreen("register")}
      onForgotPassword={() => setScreen("forgot")}
    />
  );
}
