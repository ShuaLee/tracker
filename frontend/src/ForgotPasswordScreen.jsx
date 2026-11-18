import { useState } from "react";
import { requestPasswordReset } from "./api.js";
import { DevEmailHint, Field, Message } from "./ui.jsx";
import { useAction } from "./useAction.js";

export default function ForgotPasswordScreen({ onBackToLogin }) {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const { submitting, message, run } = useAction();

  function handleSubmit(event) {
    event.preventDefault();
    run(() => requestPasswordReset(email), {
      success: (response) => response.data?.detail,
      onSuccess: () => setSent(true),
    });
  }

  return (
    <div>
      <h1>Reset your password</h1>
      {!sent && (
        <form onSubmit={handleSubmit}>
          <Field
            id="forgot_email"
            label="Email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
          <button type="submit" disabled={submitting}>
            {submitting ? "Sending..." : "Send reset link"}
          </button>
        </form>
      )}
      <Message message={message} />
      {sent && <DevEmailHint />}
      <button type="button" onClick={onBackToLogin}>
        Back to log in
      </button>
    </div>
  );
}
