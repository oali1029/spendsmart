// All backend HTTP calls live here, so components never contain fetch logic or URLs.
// Base URL comes from VITE_API_BASE_URL (see .env.example); the fallback is the local backend.
const BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1").replace(/\/$/, "");

// An error whose message is already safe and readable to show directly in the UI.
export class ApiError extends Error {
  constructor(message, status = null) {
    super(message);
    this.status = status;
  }
}

// FastAPI returns `detail` as a string (404/409/502/503) or a list of {loc, msg} (422 validation).
async function messageFromResponse(response) {
  try {
    const body = await response.json();
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail)) {
      return body.detail
        .map((d) => `${(d.loc || []).filter((p) => p !== "body").join(".")}: ${d.msg}`)
        .join("; ");
    }
  } catch {
    // body was not JSON; fall through to the generic message
  }
  return `Request failed (HTTP ${response.status}).`;
}

// No client-side timeout on purpose: the local AI model can take a minute or more to answer.
async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
  } catch {
    throw new ApiError("Can't reach the SpendSmart backend. Is it running?");
  }
  if (!response.ok) throw new ApiError(await messageFromResponse(response), response.status);
  return response.status === 204 ? null : response.json();
}

export const getSummary = (month) => request(`/summary?month=${encodeURIComponent(month)}`);

export const getExpenses = (month) => request(`/expenses?month=${encodeURIComponent(month)}`);

// `amount` is sent as the typed string ("12.50") so no floating-point rounding can creep in.
export const createExpense = ({ amount, expenseDate, categoryId, description }) =>
  request("/expenses", {
    method: "POST",
    body: JSON.stringify({
      amount,
      expense_date: expenseDate,
      category_id: categoryId,
      description: description || null,
    }),
  });

// `monthlyLimit` is optional; an empty value is sent as null, meaning "no limit". Like amounts,
// it is sent as the typed string so no floating-point rounding can creep in.
export const createCategory = ({ name, monthlyLimit }) =>
  request("/categories", {
    method: "POST",
    body: JSON.stringify({ name, monthly_limit: monthlyLimit || null }),
  });

export const getCoaches = () => request("/coaches");

// The UI neither knows nor cares how the backend executes the coach's tools.
export const sendChat = ({ coachId, message, history }) =>
  request("/chat", {
    method: "POST",
    body: JSON.stringify({ coach_id: coachId, message, history }),
  });
