import { useState } from "react";
import { createExpense } from "../api";
import { formatMonthLabel, today } from "../format";

export default function ExpenseForm({ categories, month, onCreated }) {
  const [categoryId, setCategoryId] = useState("");
  const [amount, setAmount] = useState("");
  const [date, setDate] = useState(today());
  const [description, setDescription] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);

  async function handleSubmit(event) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      await createExpense({
        amount,
        expenseDate: date,
        categoryId: Number(categoryId),
        description: description.trim(),
      });
      setAmount("");
      setDescription("");
      // An expense dated in another month is saved, but won't appear in the month being shown.
      if (!date.startsWith(month)) {
        setNotice(`Saved. It belongs to a different month than ${formatMonthLabel(month)}.`);
      } else {
        setNotice("Expense added.");
      }
      onCreated(); // refresh the dashboard
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="panel">
      <h2>Add expense</h2>
      <form onSubmit={handleSubmit} className="form">
        <label>
          Category
          <select value={categoryId} onChange={(e) => setCategoryId(e.target.value)} required>
            <option value="" disabled>
              {categories.length ? "Select a category" : "No categories available"}
            </option>
            {categories.map((c) => (
              <option key={c.category_id} value={c.category_id}>
                {c.name}
              </option>
            ))}
          </select>
        </label>
        <div className="form-row">
          <label>
            Amount
            <input
              type="number"
              inputMode="decimal"
              min="0.01"
              step="0.01"
              placeholder="0.00"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              required
            />
          </label>
          <label>
            Date
            <input type="date" value={date} onChange={(e) => setDate(e.target.value)} required />
          </label>
        </div>
        <label>
          Description (optional)
          <input
            type="text"
            maxLength={255}
            placeholder="e.g. Lunch"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </label>
        <button type="submit" disabled={saving || categories.length === 0}>
          {saving ? "Saving…" : "Add expense"}
        </button>
        {error && <p className="error" role="alert">{error}</p>}
        {notice && <p className="success">{notice}</p>}
      </form>
    </section>
  );
}
