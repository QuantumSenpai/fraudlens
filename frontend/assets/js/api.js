const API_BASE = "http://127.0.0.1:8000";

async function predictTransaction(txn) {
  const res = await fetch(`${API_BASE}/predict`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(txn),
  });
  if (!res.ok) {
    throw new Error(`Predict failed: ${res.status}`);
  }
  return res.json();
}

async function getUserHistory(userId, limit = 20) {
  const res = await fetch(`${API_BASE}/history/${userId}?limit=${limit}`);
  if (!res.ok) {
    throw new Error(`History fetch failed: ${res.status}`);
  }
  return res.json();
}

async function getStats() {
  const res = await fetch(`${API_BASE}/stats`);
  if (!res.ok) {
    throw new Error(`Stats fetch failed: ${res.status}`);
  }
  return res.json();
}