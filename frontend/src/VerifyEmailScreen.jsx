import { useEffect, useRef } from "react";
import { verifyEmail } from "./api.js";
import { Message } from "./ui.jsx";
import { useAction } from "./useAction.js";

// Landing page for the emailed /verify-email?uid=...&email=...&token=... link.
// Covers both first-time verification and confirming an email change (same
// endpoint - the backend tells them apart by comparing the email).
export default function VerifyEmailScreen({ uid, email, token, onDone }) {
  const { submitting, message, run } = useAction();
  // The token is single-use, and StrictMode runs effects twice in dev - the
  // second call would fail and overwrite the success message.
  const started = useRef(false);

  useEffect(() => {
    if (started.current || !uid || !email || !token) return;
    started.current = true;
    run(() => verifyEmail(uid, email, token), {
      success: `Email confirmed: ${email}`,
    });
    // run is recreated every render; this must fire once per mount only.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [uid, email, token]);

  return (
    <div>
      <h1>Confirm email</h1>
      {!uid || !email || !token ? (
        <p>This link is incomplete. Request a new one from your account settings.</p>
      ) : (
        <>
          {(submitting || !message) && <p>Confirming...</p>}
          <Message message={message} />
        </>
      )}
      <button type="button" onClick={onDone} disabled={submitting}>
        Continue
      </button>
    </div>
  );
}
