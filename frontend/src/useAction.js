import { useState } from "react";
import { errorMessage } from "./api.js";

// Wraps one API call: tracks "submitting", turns the response into a
// success/error message for <Message>, and catches network failures (fetch
// rejects when the backend is down instead of resolving with an error status).
export function useAction() {
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState(null);

  async function run(call, { success, onSuccess, fallback } = {}) {
    setSubmitting(true);
    setMessage(null);
    try {
      const response = await call();
      if (response.ok) {
        const text = typeof success === "function" ? success(response) : success;
        if (text) setMessage({ text });
        onSuccess?.(response);
      } else {
        setMessage({ text: errorMessage(response, fallback), error: true });
      }
      return response;
    } catch (error) {
      setMessage({ text: `Couldn't reach the server (${error.message}).`, error: true });
      return null;
    } finally {
      setSubmitting(false);
    }
  }

  return { submitting, message, setMessage, run };
}
