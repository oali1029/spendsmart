import { useCallback, useEffect, useState } from "react";
import { getExpenses, getSummary } from "./api";
import { currentMonth, formatMonthLabel } from "./format";
import CategorySpending from "./components/CategorySpending";
import CoachChat from "./components/CoachChat";
import ExpenseForm from "./components/ExpenseForm";
import ExpenseList from "./components/ExpenseList";
import SummaryCards from "./components/SummaryCards";

export default function App() {
  const [month, setMonth] = useState(currentMonth());
  const [data, setData] = useState(null); // { summary, expenses }
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  // Bumping this re-runs the data load (used after adding an expense and by "Retry").
  const [version, setVersion] = useState(0);
  const refresh = useCallback(() => setVersion((v) => v + 1), []);

  useEffect(() => {
    // `ignore` drops the response of an outdated request (e.g. the user changed month quickly).
    let ignore = false;
    setLoading(true);
    Promise.all([getSummary(month), getExpenses(month)])
      .then(([summary, expenses]) => {
        if (ignore) return;
        setData({ summary, expenses });
        setError(null);
      })
      .catch((e) => !ignore && setError(e.message))
      .finally(() => !ignore && setLoading(false));
    return () => {
      ignore = true;
    };
  }, [month, version]);

  // The summary lists every category with its id, name, spending and limit, so it feeds the
  // category section, the expense form's dropdown and the expense list's category names.
  const categories = data?.summary.categories ?? [];

  return (
    <div className="app">
      <header className="header">
        <div>
          <h1>SpendSmart</h1>
          <p className="muted">{formatMonthLabel(month)}</p>
        </div>
        <label className="month-picker">
          Month
          <input
            type="month"
            value={month}
            onChange={(e) => e.target.value && setMonth(e.target.value)}
          />
        </label>
      </header>

      {error && (
        <div className="banner" role="alert">
          <span>Couldn't load your dashboard: {error}</span>
          <button type="button" onClick={refresh}>Retry</button>
        </div>
      )}

      <main className="layout">
        <div className={`dashboard ${loading ? "refreshing" : ""}`}>
          {data ? (
            <>
              <SummaryCards summary={data.summary} />
              <CategorySpending categories={categories} onCategoryCreated={refresh} />
              <ExpenseList expenses={data.expenses} categories={categories} />
              <ExpenseForm categories={categories} month={month} onCreated={refresh} />
            </>
          ) : (
            !error && <p className="muted">Loading your dashboard…</p>
          )}
        </div>
        <aside className="coach-column">
          <CoachChat />
        </aside>
      </main>
    </div>
  );
}
