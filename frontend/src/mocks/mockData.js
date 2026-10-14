// Donnees factices utilisees quand REACT_APP_USE_MOCKS=true.
// Les formes reprennent celles des serializers Django (transactions, alerts).

// Generateur pseudo-aleatoire deterministe : memes donnees a chaque rechargement.
function createRandom(seed) {
  let state = seed;
  return () => {
    state = (state * 1664525 + 1013904223) % 4294967296;
    return state / 4294967296;
  };
}

const random = createRandom(42);
const pick = (items) => items[Math.floor(random() * items.length)];

const CHANNELS = ["card", "mobile_money", "transfer", "online"];
const MERCHANTS = ["Auchan Dakar", "Orange Money", "Jumia", "Total Energies", "Wave", "Casino", "Air Senegal"];
const LOCATIONS = ["Dakar", "Thies", "Saint-Louis", "Ziguinchor", "Paris", "Abidjan"];
const DEVICES = ["iPhone 14", "Samsung A54", "Chrome / Windows", "Firefox / Linux", "TPE-0042"];

export const MOCK_USERS = [
  { id: 1, username: "admin", password: "admin", role: "admin", email: "admin@fraudguard.local" },
  { id: 2, username: "analyste", password: "analyste", role: "analyst", email: "analyste@fraudguard.local" },
];

function weightedStatus() {
  const r = random();
  if (r < 0.7) return "legitimate";
  if (r < 0.82) return "pending";
  if (r < 0.92) return "under_review";
  return "fraudulent";
}

function buildTransactions(total) {
  const now = Date.now();
  return Array.from({ length: total }, (_, i) => {
    const id = i + 1;
    const timestamp = new Date(now - id * 37 * 60 * 1000).toISOString();
    return {
      id,
      transaction_id: `TXN-${String(100000 + id)}`,
      amount: (random() * 950000 + 500).toFixed(2),
      merchant: pick(MERCHANTS),
      device: pick(DEVICES),
      location: pick(LOCATIONS),
      channel: pick(CHANNELS),
      timestamp,
      status: weightedStatus(),
      created_by: 1,
      created_at: timestamp,
    };
  });
}

function buildAlerts(transactions) {
  const suspicious = transactions.filter((t) => t.status === "fraudulent" || t.status === "under_review");
  return suspicious.map((t, i) => {
    const r = random();
    const status = r < 0.6 ? "open" : r < 0.75 ? "confirmed" : r < 0.9 ? "rejected" : "resolved";
    return {
      id: i + 1,
      prediction: t.id,
      assigned_to: status === "open" ? null : 2,
      status,
      severity: t.status === "fraudulent" ? pick(["high", "critical"]) : pick(["low", "medium"]),
      comment: "",
      created_at: t.timestamp,
      resolved_at: status === "open" ? null : new Date().toISOString(),
    };
  });
}

export const transactions = buildTransactions(137);
export const alerts = buildAlerts(transactions);
