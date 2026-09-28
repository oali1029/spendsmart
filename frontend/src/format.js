// Display helpers. The backend sends money as strings ("50.00"); numbers here are for display only.
const money = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" });

export const formatMoney = (value) => (value == null ? "—" : money.format(Number(value)));

// "2026-09-05" -> "Sep 5, 2026". Parsed as local midnight so the day never shifts across timezones.
export const formatDate = (iso) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });

// "2026-09" -> "September 2026"
export function formatMonthLabel(yearMonth) {
  const [year, month] = yearMonth.split("-").map(Number);
  return new Date(year, month - 1, 1).toLocaleDateString("en-US", { month: "long", year: "numeric" });
}

const pad = (n) => String(n).padStart(2, "0");

export function currentMonth() {
  const now = new Date();
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}`;
}

export function today() {
  const now = new Date();
  return `${currentMonth()}-${pad(now.getDate())}`;
}
