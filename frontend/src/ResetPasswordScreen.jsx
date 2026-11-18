import { useState } from "react";
import { confirmPasswordReset } from "./api.js";
import { Field, Message } from "./ui.jsx";
import { useAction } from "./useAction.js";

// Landing page for the emailed /reset-password?uid=...&token=... link.
export default function ResetPasswordScreen({ uid, token, onDone }) {
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [done, setDone] = useState(false);
  const { submitting, message, setMessage, run } = useAction();

  function handleSubmit(event) {
    event.preventDefault();
    if (newPassword !== confirmPassword) {
      setMessage({ text: "The passwords don't match.", error: true });
      return;
    }
    run(() => confirmPasswordReset(uid, token, newPassword), {
      success: "Password reset. Every session was signed out - log in with the new password.",
      onSuccess: () => setDone(true),
    });
  }

  if (!uid || !token) {
    return (
      <div>
        <h1>Reset your password</h1>
        <p>This link is incomplete. Request a new one from the log in screen.</p>
        <button type="button" onClick={onDone}>
          Go to log in
        </button>
      </div>
    );
  }

  return (
    <div>
      <h1>Choose a new password</h1>
      {!done && (
        <form onSubmit={handleSubmit}>
          <Field
            id="reset_new_password"
            label="New password (12+ characters)"
            type="password"
            autoComplete="new-password"
            value={newPassword}
            onChange={(event) => setNewPassword(event.target.value)}
            required
          />
          <Field
            id="reset_confirm_password"
            label="Confirm new password"
            type="password"
            autoComplete="new-password"
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
            required
          />
          <button type="submit" disabled={submitting}>
            {submitting ? "Saving..." : "Set new password"}
          </button>
        </form>
      )}
      <Message message={message} />
      <button type="button" onClick={onDone}>
        {done ? "Go to log in" : "Cancel"}
      </button>
    </div>
  );
}
