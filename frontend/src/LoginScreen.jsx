import { useState } from "react";
import { login } from "./api.js";
import { Field, Message } from "./ui.jsx";
import { useAction } from "./useAction.js";

export default function LoginScreen({ onLoggedIn, onCreateAccount, onForgotPassword }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const { submitting, message, run } = useAction();

  function handleSubmit(event) {
    event.preventDefault();
    run(() => login(email, password), {
      fallback: "Login failed.",
      onSuccess: (response) => onLoggedIn(response.data),
    });
  }

  return (
    <div>
      <h1>Log in</h1>
      <form onSubmit={handleSubmit}>
        <Field
          id="email"
          label="Email"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          required
        />
        <Field
          id="password"
          label="Password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          required
        />
        <button type="submit" disabled={submitting}>
          {submitting ? "Logging in..." : "Log in"}
        </button>
      </form>
      <Message message={message} />

      <p>
        <button type="button" onClick={onForgotPassword}>
          Forgot password?
        </button>
      </p>
      <p>
        No account yet?{" "}
        <button type="button" onClick={onCreateAccount}>
          Create account
        </button>
      </p>
    </div>
  );
}
