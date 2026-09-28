import { useState } from "react";
import { createCategory } from "../api";

export default function CategoryForm({ onCreated, onCancel }) {
  const [name, setName] = useState("");
  const [monthlyLimit, setMonthlyLimit] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit(event) {
    event.preventDefault();
    const trimmed = name.trim();
    // `required` lets whitespace through, so check it here.
    if (!trimmed) {
      setError("Please enter a category name.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await createCategory({ name: trimmed, monthlyLimit });
      onCreated(); // parent closes this form and refreshes the dashboard
    } catch (e) {
      // e.g. 409 "Category 'Food' already exists" or a 422 validation message
      setError(e.message);
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="form inline-form">
      <div className="form-row">
        <label>
          Category name
          <input
            type="text"
            maxLength={100}
            placeholder="e.g. Groceries"
            value={name}
            onChange={(e) => setName(e.target.value)}
            autoFocus
            required
          />
        </label>
        <label>
          Monthly limit (optional)
          <input
            type="number"
            inputMode="decimal"
            min="0.01"
            step="0.01"
            placeholder="No limit"
            value={monthlyLimit}
            onChange={(e) => setMonthlyLimit(e.target.value)}
          />
        </label>
      </div>
      <div className="form-actions">
        <button type="submit" disabled={saving}>
          {saving ? "Saving…" : "Save category"}
        </button>
        <button type="button" className="btn-secondary" onClick={onCancel} disabled={saving}>
          Cancel
        </button>
      </div>
      {error && <p className="error" role="alert">{error}</p>}
    </form>
  );
}
