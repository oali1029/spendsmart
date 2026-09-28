import { formatMoney } from "../format";

export default function SummaryCards({ summary }) {
  const { budget, total_spent: spent, remaining } = summary;
  const over = remaining != null && Number(remaining) < 0;

  return (
    <section className="cards" aria-label="Monthly summary">
      <div className="card">
        <span className="card-label">Monthly Budget</span>
        <span className="card-value">{budget == null ? "Not set" : formatMoney(budget)}</span>
        {budget == null && <span className="card-note">No budget for this month yet</span>}
      </div>
      <div className="card">
        <span className="card-label">Total Spent</span>
        <span className="card-value">{formatMoney(spent)}</span>
      </div>
      <div className="card">
        <span className="card-label">Remaining</span>
        <span className={`card-value ${over ? "negative" : remaining != null ? "positive" : ""}`}>
          {formatMoney(remaining)}
        </span>
        {over && <span className="card-note negative">Over budget</span>}
      </div>
    </section>
  );
}
