const BASE = "/api";

async function handle(res) {
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status}: ${body}`);
  }
  return res.json();
}

export const api = {
  listVendors: () => fetch(`${BASE}/vendors`).then(handle),
  createVendor: (payload) =>
    fetch(`${BASE}/vendors`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }).then(handle),
  getVendorFindings: (id) => fetch(`${BASE}/vendors/${id}/findings`).then(handle),
  scoreVendor: (id) => fetch(`${BASE}/score/${id}`, { method: "POST" }).then(handle),
};
