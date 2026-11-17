import { useState } from "react";
import { logout, updateProfile } from "./api.js";

// Mirrors accounts.models.Profile's choices (backend/accounts/models.py).
// No endpoint exposes these dynamically yet - keep in sync by hand for now.
const CURRENCIES = ["CAD", "USD", "EUR", "GBP", "AUD", "CHF", "JPY"];
const ROLES = [
  ["individual", "Individual"],
  ["advisor", "Advisor"],
];

export default function SettingsScreen({ me, onUpdated, onLoggedOut }) {
  const [displayName, setDisplayName] = useState(me.profile.display_name);
  const [baseCurrency, setBaseCurrency] = useState(me.profile.base_currency);
  const [timezone, setTimezone] = useState(me.profile.timezone);
  const [role, setRole] = useState(me.profile.role);
  const [status, setStatus] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setSubmitting(true);
    setStatus(null);

    const response = await updateProfile({
      display_name: displayName,
      base_currency: baseCurrency,
      timezone,
      role,
    });
    setSubmitting(false);

    if (response.ok) {
      setStatus("Saved.");
      onUpdated(response.data);
    } else {
      setStatus("Failed to save.");
    }
  }

  async function handleLogout() {
    await logout();
    onLoggedOut();
  }

  return (
    <div>
      <h1>Settings</h1>
      <p>
        {me.email} {me.is_email_verified ? "(verified)" : "(not verified)"}
      </p>

      <form onSubmit={handleSubmit}>
        <div>
          <label htmlFor="display_name">Display name</label>
          <input
            id="display_name"
            type="text"
            value={displayName}
            onChange={(event) => setDisplayName(event.target.value)}
          />
        </div>
        <div>
          <label htmlFor="base_currency">Base currency</label>
          <select
            id="base_currency"
            value={baseCurrency}
            onChange={(event) => setBaseCurrency(event.target.value)}
          >
            {CURRENCIES.map((code) => (
              <option key={code} value={code}>
                {code}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="timezone">Timezone</label>
          <input
            id="timezone"
            type="text"
            value={timezone}
            onChange={(event) => setTimezone(event.target.value)}
          />
        </div>
        <div>
          <label htmlFor="role">Role</label>
          <select id="role" value={role} onChange={(event) => setRole(event.target.value)}>
            {ROLES.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>
        <button type="submit" disabled={submitting}>
          {submitting ? "Saving..." : "Save"}
        </button>
      </form>
      {status && <p>{status}</p>}

      <button type="button" onClick={handleLogout}>
        Log out
      </button>
    </div>
  );
}
