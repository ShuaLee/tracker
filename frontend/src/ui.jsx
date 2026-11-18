// Shared bits for the auth screens. Unstyled on purpose (see index.css).

export function Field({ id, label, ...inputProps }) {
  return (
    <div>
      <label htmlFor={id}>{label}</label> <input id={id} {...inputProps} />
    </div>
  );
}

export function Message({ message }) {
  if (!message) return null;
  // pre-line: errorMessage() joins multiple field errors with newlines.
  return (
    <p role={message.error ? "alert" : "status"} style={{ whiteSpace: "pre-line" }}>
      {message.error ? "Error: " : ""}
      {message.text}
    </p>
  );
}

// Dev-only hint: the console email backend prints links in the runserver
// terminal instead of sending them.
export function DevEmailHint() {
  if (!import.meta.env.DEV) return null;
  return <p>(Dev: emails aren't really sent - the link is printed in the runserver terminal.)</p>;
}
