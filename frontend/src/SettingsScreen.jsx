import { useEffect, useState } from "react";
import {
  changeEmail,
  changePassword,
  deactivateAccount,
  fetchOptions,
  fetchSecurityEvents,
  logout,
  logoutAll,
  resendVerification,
  updateProfile,
} from "./api.js";
import { DevEmailHint, Field, Message } from "./ui.jsx";
import { useAction } from "./useAction.js";

export default function SettingsScreen({ me, onUpdated, onLoggedOut }) {
  const { submitting: loggingOut, run } = useAction();

  return (
    <div>
      <h1>Settings</h1>
      <AccountSection me={me} />
      <ProfileSection me={me} onUpdated={onUpdated} />
      <ChangePasswordSection />
      <ChangeEmailSection me={me} />
      <SessionsSection onLoggedOut={onLoggedOut} />
      <SecurityActivitySection />
      <DeactivateSection onDeactivated={onLoggedOut} />
      <hr />
      <button
        type="button"
        disabled={loggingOut}
        onClick={() => run(logout, { onSuccess: onLoggedOut })}
      >
        Log out
      </button>
    </div>
  );
}

function AccountSection({ me }) {
  const { submitting, message, run } = useAction();

  return (
    <section>
      <h2>Account</h2>
      <p>Email: {me.email}</p>
      <p>Email status: {me.is_email_verified ? "verified" : "not verified"}</p>
      <p>Role: {me.profile.role} (set by an administrator)</p>
      <p>Member since: {new Date(me.date_joined).toLocaleDateString()}</p>
      {!me.is_email_verified && (
        <>
          <button
            type="button"
            disabled={submitting}
            onClick={() =>
              run(() => resendVerification(me.email), {
                success: (response) => response.data?.detail,
              })
            }
          >
            {submitting ? "Sending..." : "Resend verification email"}
          </button>
          <Message message={message} />
          {message && !message.error && <DevEmailHint />}
        </>
      )}
    </section>
  );
}

function ProfileSection({ me, onUpdated }) {
  const [displayName, setDisplayName] = useState(me.profile.display_name);
  const [baseCurrency, setBaseCurrency] = useState(me.profile.base_currency);
  const [timezone, setTimezone] = useState(me.profile.timezone);
  // Choices come from the backend (options/), so they can't drift from
  // accounts.models.Profile. Until they load, show just the saved values.
  const [options, setOptions] = useState({
    currencies: [{ value: me.profile.base_currency, label: me.profile.base_currency }],
    timezones: [me.profile.timezone],
  });
  const { submitting, message, setMessage, run } = useAction();

  useEffect(() => {
    let cancelled = false;
    fetchOptions()
      .then((response) => {
        if (!cancelled && response.ok) setOptions(response.data);
      })
      .catch(() => {
        if (!cancelled) setMessage({ text: "Couldn't load the currency/timezone lists.", error: true });
      });
    return () => {
      cancelled = true;
    };
  }, [setMessage]);

  function handleSubmit(event) {
    event.preventDefault();
    run(
      () => updateProfile({ display_name: displayName, base_currency: baseCurrency, timezone }),
      { success: "Saved.", fallback: "Failed to save.", onSuccess: (response) => onUpdated(response.data) },
    );
  }

  return (
    <section>
      <h2>Profile</h2>
      <form onSubmit={handleSubmit}>
        <Field
          id="display_name"
          label="Display name"
          type="text"
          value={displayName}
          onChange={(event) => setDisplayName(event.target.value)}
        />
        <div>
          <label htmlFor="base_currency">Base currency</label>{" "}
          <select
            id="base_currency"
            value={baseCurrency}
            onChange={(event) => setBaseCurrency(event.target.value)}
          >
            {options.currencies.map(({ value, label }) => (
              <option key={value} value={value}>
                {value === label ? value : `${value} - ${label}`}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="timezone">Timezone</label>{" "}
          <select id="timezone" value={timezone} onChange={(event) => setTimezone(event.target.value)}>
            {options.timezones.map((zone) => (
              <option key={zone} value={zone}>
                {zone}
              </option>
            ))}
          </select>
        </div>
        <button type="submit" disabled={submitting}>
          {submitting ? "Saving..." : "Save profile"}
        </button>
      </form>
      <Message message={message} />
    </section>
  );
}

function ChangePasswordSection() {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const { submitting, message, setMessage, run } = useAction();

  function handleSubmit(event) {
    event.preventDefault();
    if (newPassword !== confirmPassword) {
      setMessage({ text: "The new passwords don't match.", error: true });
      return;
    }
    run(() => changePassword(currentPassword, newPassword), {
      success: "Password changed. Your other sessions were signed out; this one stays logged in.",
      onSuccess: () => {
        setCurrentPassword("");
        setNewPassword("");
        setConfirmPassword("");
      },
    });
  }

  return (
    <section>
      <h2>Change password</h2>
      <form onSubmit={handleSubmit}>
        <Field
          id="cp_current"
          label="Current password"
          type="password"
          autoComplete="current-password"
          value={currentPassword}
          onChange={(event) => setCurrentPassword(event.target.value)}
          required
        />
        <Field
          id="cp_new"
          label="New password (12+ characters)"
          type="password"
          autoComplete="new-password"
          value={newPassword}
          onChange={(event) => setNewPassword(event.target.value)}
          required
        />
        <Field
          id="cp_confirm"
          label="Confirm new password"
          type="password"
          autoComplete="new-password"
          value={confirmPassword}
          onChange={(event) => setConfirmPassword(event.target.value)}
          required
        />
        <button type="submit" disabled={submitting}>
          {submitting ? "Changing..." : "Change password"}
        </button>
      </form>
      <Message message={message} />
    </section>
  );
}

function ChangeEmailSection({ me }) {
  const [newEmail, setNewEmail] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const { submitting, message, setMessage, run } = useAction();

  function handleSubmit(event) {
    event.preventDefault();
    if (newEmail.trim().toLowerCase() === me.email) {
      setMessage({ text: "That's already your email.", error: true });
      return;
    }
    // Nothing changes until the link sent to the new address is clicked.
    run(() => changeEmail(newEmail, currentPassword), {
      success: (response) =>
        `${response.data?.detail} Your email stays ${me.email} until you click it.`,
      onSuccess: () => setCurrentPassword(""),
    });
  }

  return (
    <section>
      <h2>Change email</h2>
      <form onSubmit={handleSubmit}>
        <Field
          id="ce_new_email"
          label="New email"
          type="email"
          autoComplete="email"
          value={newEmail}
          onChange={(event) => setNewEmail(event.target.value)}
          required
        />
        <Field
          id="ce_current_password"
          label="Current password"
          type="password"
          autoComplete="current-password"
          value={currentPassword}
          onChange={(event) => setCurrentPassword(event.target.value)}
          required
        />
        <button type="submit" disabled={submitting}>
          {submitting ? "Sending..." : "Send confirmation link"}
        </button>
      </form>
      <Message message={message} />
      {message && !message.error && <DevEmailHint />}
    </section>
  );
}

function SessionsSection({ onLoggedOut }) {
  const { submitting, message, run } = useAction();

  function signOutOthers() {
    run(() => logoutAll(true), { success: (response) => response.data?.detail });
  }

  function signOutEverywhere() {
    if (!window.confirm("Sign out of every device, including this one?")) return;
    run(() => logoutAll(false), { onSuccess: onLoggedOut });
  }

  return (
    <section>
      <h2>Sessions</h2>
      <p>If you think someone else is signed in to your account, sign out everywhere and change your password.</p>
      <button type="button" disabled={submitting} onClick={signOutOthers}>
        Sign out other devices
      </button>{" "}
      <button type="button" disabled={submitting} onClick={signOutEverywhere}>
        Sign out everywhere
      </button>
      <Message message={message} />
    </section>
  );
}

function SecurityActivitySection() {
  const [events, setEvents] = useState(null);
  const { submitting, message, run } = useAction();

  function load() {
    run(fetchSecurityEvents, { onSuccess: (response) => setEvents(response.data) });
  }

  useEffect(() => {
    load();
    // Load once on mount; the Refresh button handles the rest.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <section>
      <h2>Recent security activity</h2>
      <button type="button" disabled={submitting} onClick={load}>
        {submitting ? "Loading..." : "Refresh"}
      </button>
      <Message message={message} />
      {events && events.length === 0 && <p>No activity yet.</p>}
      {events && events.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>When</th>
              <th>What</th>
              <th>IP address</th>
              <th>Device</th>
            </tr>
          </thead>
          <tbody>
            {events.map((event, index) => (
              <tr key={`${event.created_at}-${index}`}>
                <td>{new Date(event.created_at).toLocaleString()}</td>
                <td>{event.event_label}</td>
                <td>{event.ip || "-"}</td>
                <td title={event.user_agent}>{event.user_agent ? event.user_agent.slice(0, 50) : "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

function DeactivateSection({ onDeactivated }) {
  const [currentPassword, setCurrentPassword] = useState("");
  const { submitting, message, run } = useAction();

  function handleSubmit(event) {
    event.preventDefault();
    if (!window.confirm("Deactivate your account? You'll be logged out everywhere and won't be able to log back in.")) {
      return;
    }
    run(() => deactivateAccount(currentPassword), { onSuccess: onDeactivated });
  }

  return (
    <section>
      <h2>Delete account</h2>
      <p>
        This deactivates your account: you're logged out on every device and can't log in again.
        Your data is kept, and an admin can reactivate the account.
      </p>
      <form onSubmit={handleSubmit}>
        <Field
          id="da_current_password"
          label="Current password"
          type="password"
          autoComplete="current-password"
          value={currentPassword}
          onChange={(event) => setCurrentPassword(event.target.value)}
          required
        />
        <button type="submit" disabled={submitting}>
          {submitting ? "Deactivating..." : "Deactivate account"}
        </button>
      </form>
      <Message message={message} />
    </section>
  );
}
