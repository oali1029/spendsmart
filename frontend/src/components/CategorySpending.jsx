import { useState } from "react";
import { formatMoney } from "../format";
import CategoryForm from "./CategoryForm";

const ADD_NEW = "__add_new__";

// Green normally, amber from 80% of the category limit, red once it is exceeded.
function barState(percent) {
  if (percent > 100) return "over";
  if (percent >= 80) return "warn";
  return "ok";
}

export default function CategorySpending({ categories, onCategoryCreated }) {
  const [adding, setAdding] = useState(false);

  return (
    <section className="panel">
      <div className="panel-header">
        <h2>Spending by category</h2>
        {/* A menu of the existing categories (greyed out: reference only) ending in the one
            selectable action. The value stays "" so the menu always resets to its label. */}
        <select
          className="category-menu"
          value=""
          aria-label="Categories menu"
          onChange={(e) => e.target.value === ADD_NEW && setAdding(true)}
        >
          <option value="">Categories ({categories.length})</option>
          {categories.map((c) => (
            <option key={c.category_id} disabled>
              {c.name}
              {c.monthly_limit != null ? ` — limit ${formatMoney(c.monthly_limit)}` : " — no limit"}
            </option>
          ))}
          <option value={ADD_NEW}>+ Add new category…</option>
        </select>
      </div>

      {adding && (
        <CategoryForm
          onCancel={() => setAdding(false)}
          onCreated={() => {
            setAdding(false); // close (and thereby clear) the form
            onCategoryCreated(); // refresh: the summary now includes the new category
          }}
        />
      )}

      {categories.length === 0 ? (
        <p className="muted">No categories yet. Add your first one to start tracking expenses.</p>
      ) : (
        <ul className="category-list">
          {categories.map((c) => {
            const hasLimit = c.monthly_limit != null;
            const percent = hasLimit ? (Number(c.spent) / Number(c.monthly_limit)) * 100 : 0;
            return (
              <li key={c.category_id}>
                <div className="row">
                  <strong>{c.name}</strong>
                  <span>
                    {formatMoney(c.spent)}
                    {hasLimit ? <span className="muted"> of {formatMoney(c.monthly_limit)}</span> : null}
                  </span>
                </div>
                {hasLimit ? (
                  <div
                    className="bar"
                    role="progressbar"
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-valuenow={Math.min(Math.round(percent), 100)}
                    aria-label={`${c.name} spending against its limit`}
                  >
                    <div className={`bar-fill ${barState(percent)}`} style={{ width: `${Math.min(percent, 100)}%` }} />
                  </div>
                ) : (
                  <span className="muted small">No monthly limit</span>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
