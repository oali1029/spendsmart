import { formatDate, formatMoney } from "../format";

const SHOWN = 10;

// Expenses only carry a category_id, so names come from the summary's category list.
export default function ExpenseList({ expenses, categories }) {
  const names = Object.fromEntries(categories.map((c) => [c.category_id, c.name]));
  const recent = expenses.slice(0, SHOWN); // the API returns newest first

  return (
    <section className="panel">
      <h2>Recent expenses</h2>
      {recent.length === 0 ? (
        <p className="muted">No expenses in this month.</p>
      ) : (
        <ul className="expense-list">
          {recent.map((e) => (
            <li key={e.id}>
              <div className="row">
                <strong>{names[e.category_id] ?? "Unknown category"}</strong>
                <span>{formatMoney(e.amount)}</span>
              </div>
              <div className="row muted small">
                <span>{e.description || "No description"}</span>
                <span>{formatDate(e.expense_date)}</span>
              </div>
            </li>
          ))}
        </ul>
      )}
      {expenses.length > SHOWN && (
        <p className="muted small">
          Showing the latest {SHOWN} of {expenses.length} expenses this month.
        </p>
      )}
    </section>
  );
}
