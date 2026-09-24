const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function sendAudit(body: Record<string, unknown>): void {
  fetch(`${API_URL}/audit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }).catch(() => {});
}
