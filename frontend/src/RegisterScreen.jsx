import { useState } from "react";
import { register } from "./api.js";
import { DevEmailHint, Field, Message } from "./ui.jsx";
import { useAction } from "./useAction.js";

export default function RegisterScreen({ onBackToLogin }) {
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [done, setDone] = useState(false);
  const { submitting, message, setMessage, run } = useAction();

  function handleSubmit(event) {
    event.preventDefault();
    if (password !== confirmPassword) {
      setMessage({ text: "The passwords don't match.", error: true });
      return;
    }
    // The backend answers identically whether or not the email is already
    // registered, and never logs the new account in - so the only next step
    // is "check your email, then log in".
    run(() => register(email, password, displayName), {
      fallback: "Couldn't create the account.",
      success: (response) => response.data?.detail,
      onSuccess: () => setDone(true),
    });
  }

  if (done) {
    return (
      <div>
        <h1>Check your email</h1>
        <Message message={message} />
        <DevEmailHint />
        <p>You can log in now. Verifying your email can happen any time.</p>
        <button type="button" onClick={onBackToLogin}>
          Go to log in
        </button>
      </div>
    );
  }

  return (
    <div>
      <h1>Create account</h1>
      <form onSubmit={handleSubmit}>
        <Field
          id="reg_email"
          label="Email"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          required
        />
        <Field
          id="reg_display_name"
          label="Display name (optional)"
          type="text"
          autoComplete="nickname"
          value={displayName}
          onChange={(event) => setDisplayName(event.target.value)}
        />
        <Field
          id="reg_password"
          label="Password (12+ characters)"
          type="password"
          autoComplete="new-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          required
        />
        <Field
          id="reg_confirm_password"
          label="Confirm password"
          type="password"
          autoComplete="new-password"
          value={confirmPassword}
          onChange={(event) => setConfirmPassword(event.target.value)}
          required
        />
        <button type="submit" disabled={submitting}>
          {submitting ? "Creating..." : "Create account"}
        </button>
      </form>
      <Message message={message} />
      <p>
        Already have an account?{" "}
        <button type="button" onClick={onBackToLogin}>
          Log in
        </button>
      </p>
    </div>
  );
}
