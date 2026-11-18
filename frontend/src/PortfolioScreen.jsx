import { useEffect, useState } from "react";
import { fetchOptions, listPortfolios, updatePortfolio } from "./api.js";
import { Field, Message } from "./ui.jsx";
import { useAction } from "./useAction.js";

// The user's one portfolio (created at signup). Holdings inside it come in
// the next step (PLAN.md B2.5).
export default function PortfolioScreen() {
  const [portfolio, setPortfolio] = useState(null);
  const [currencies, setCurrencies] = useState([]);
  const { message, run } = useAction();

  useEffect(() => {
    run(listPortfolios, {
      // Every user has exactly one portfolio.
      onSuccess: (response) => setPortfolio(response.data[0] || null),
    });
    fetchOptions()
      .then((response) => response.ok && setCurrencies(response.data.currencies))
      .catch(() => {});
    // Load once on mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div>
      <h1>Portfolio</h1>
      <Message message={message} />
      {portfolio === null ? (
        !message && <p>Loading...</p>
      ) : (
        <PortfolioForm key={portfolio.id} portfolio={portfolio} currencies={currencies} onSaved={setPortfolio} />
      )}
      <p>Accounts and holdings for this portfolio come in the next step.</p>
    </div>
  );
}

function PortfolioForm({ portfolio, currencies, onSaved }) {
  const [name, setName] = useState(portfolio.name);
  const [currency, setCurrency] = useState(portfolio.base_currency);
  const { submitting, message, run } = useAction();
  // Until options/ loads, at least show the current value.
  const choices = currencies.length ? currencies : [{ value: currency, label: currency }];

  function handleSubmit(event) {
    event.preventDefault();
    run(() => updatePortfolio(portfolio.id, { name, base_currency: currency }), {
      success: "Saved.",
      onSuccess: (response) => onSaved(response.data),
    });
  }

  return (
    <form onSubmit={handleSubmit}>
      <Field
        id="portfolio_name"
        label="Name"
        type="text"
        value={name}
        onChange={(event) => setName(event.target.value)}
        required
      />
      <div>
        <label htmlFor="portfolio_currency">Base currency</label>{" "}
        <select id="portfolio_currency" value={currency} onChange={(event) => setCurrency(event.target.value)}>
          {choices.map((option) => (
            <option key={option.value} value={option.value}>
              {option.value === option.label ? option.value : `${option.value} - ${option.label}`}
            </option>
          ))}
        </select>
      </div>
      <p>Created {new Date(portfolio.created_at).toLocaleDateString()}</p>
      <button type="submit" disabled={submitting}>
        {submitting ? "Saving..." : "Save portfolio"}
      </button>
      <Message message={message} />
    </form>
  );
}
