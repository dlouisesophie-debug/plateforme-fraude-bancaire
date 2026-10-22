// Données factices utilisées quand REACT_APP_USE_MOCKS=true.
// Les formes reprennent celles des serializers Django (transactions, alerts,
// utilisateurs, modèles ML, rapports).

// Générateur pseudo-aléatoire déterministe : mêmes données à chaque rechargement.
function createRandom(seed) {
  let state = seed;
  return () => {
    state = (state * 1664525 + 1013904223) % 4294967296;
    return state / 4294967296;
  };
}

const random = createRandom(42);
const pick = (items) => items[Math.floor(random() * items.length)];
const between = (min, max) => min + random() * (max - min);

const CHANNELS = ["card", "mobile_money", "transfer", "online"];
const MERCHANTS = ["Auchan Dakar", "Orange Money", "Jumia", "Total Energies", "Wave", "Casino", "Air Sénégal"];
const CATEGORIES = ["achats", "courses", "restauration", "voyage", "achats_en_ligne", "divertissement", "maison"];
const CITIES = [
  { city: "Dakar", region: "Dakar", population: 1200000, lat: 14.6928, lon: -17.4467 },
  { city: "Thiès", region: "Thiès", population: 320000, lat: 14.791, lon: -16.9359 },
  { city: "Saint-Louis", region: "Saint-Louis", population: 210000, lat: 16.0179, lon: -16.4896 },
  { city: "Ziguinchor", region: "Ziguinchor", population: 205000, lat: 12.5681, lon: -16.2733 },
  { city: "Kaolack", region: "Kaolack", population: 230000, lat: 14.1652, lon: -16.0758 },
];
const DEVICES = ["mobile", "web", "TPE-0042", "Samsung A54", "iPhone 14"];

export const ACTIVE_MODEL_VERSION = "1.0.0";
export const DECISION_THRESHOLD = 0.1126;

export const MOCK_USERS = [
  { id: 1, username: "admin", first_name: "Awa", last_name: "Ndiaye", email: "admin@fraudguard.local", role: "admin", role_label: "Administrateur", is_active: true },
  { id: 2, username: "analyste", first_name: "Moussa", last_name: "Diop", email: "analyste@fraudguard.local", role: "analyst", role_label: "Analyste Fraude", is_active: true },
  { id: 3, username: "agent", first_name: "Fatou", last_name: "Sarr", email: "agent@fraudguard.local", role: "agent", role_label: "Agent Financier", is_active: true },
];

export const mlModels = [
  {
    id: 2,
    version: ACTIVE_MODEL_VERSION,
    algorithm: "xgboost",
    precision_score: 0.91,
    recall_score: 0.87,
    f1_score: 0.89,
    auc_roc: 0.98,
    trained_at: "2026-09-28T10:00:00Z",
    is_active: true,
    artifact_path: "ml/models/fraudguard_pipeline.joblib",
  },
  {
    id: 1,
    version: "0.9.0",
    algorithm: "random_forest",
    precision_score: 0.84,
    recall_score: 0.79,
    f1_score: 0.81,
    auc_roc: 0.95,
    trained_at: "2026-09-10T10:00:00Z",
    is_active: false,
    artifact_path: "ml/models/rf_v0.joblib",
  },
];

export function severityFor(probability) {
  if (probability >= 0.9) return "critical";
  if (probability >= 0.6) return "high";
  if (probability >= 0.3) return "medium";
  return "low";
}

function weightedStatus() {
  const r = random();
  if (r < 0.7) return "legitimate";
  if (r < 0.82) return "pending";
  if (r < 0.92) return "under_review";
  return "fraudulent";
}

function probabilityFor(status) {
  // Quelques erreurs du modèle pour une matrice de confusion réaliste.
  if (status === "fraudulent") return random() < 0.1 ? between(0.02, 0.1) : between(0.6, 0.99);
  if (status === "under_review") return between(0.12, 0.6);
  if (status === "pending") return random() < 0.5 ? null : between(0, 0.1);
  return random() < 0.08 ? between(0.12, 0.4) : between(0, 0.08);
}

function buildTransactions(total) {
  const now = Date.now();
  return Array.from({ length: total }, (_, i) => {
    const id = i + 1;
    // Étalées sur ~30 jours pour alimenter la courbe journalière.
    const timestamp = new Date(now - id * 5 * 3600 * 1000 - between(0, 3600 * 1000)).toISOString();
    const status = weightedStatus();
    const place = pick(CITIES);
    const probability = probabilityFor(status);
    return {
      id,
      transaction_id: `TXN-${String(100000 + id)}`,
      amount: (random() * 950000 + 500).toFixed(2),
      merchant: pick(MERCHANTS),
      device: pick(DEVICES),
      location: place.city,
      channel: pick(CHANNELS),
      timestamp,
      status,
      category: pick(CATEGORIES),
      customer_gender: pick(["F", "M"]),
      customer_birth_date: `19${60 + Math.floor(random() * 40)}-0${1 + Math.floor(random() * 9)}-1${Math.floor(random() * 9)}`,
      customer_city: place.city,
      customer_region: place.region,
      customer_city_population: place.population,
      customer_profession: pick(["Commerçant", "Enseignante", "Ingénieur", "Étudiante", "Chauffeur"]),
      customer_latitude: place.lat,
      customer_longitude: place.lon,
      merchant_latitude: place.lat + between(-0.05, 0.05),
      merchant_longitude: place.lon + between(-0.05, 0.05),
      fraud_probability: probability === null ? null : Number(probability.toFixed(4)),
      model_version: probability === null ? null : ACTIVE_MODEL_VERSION,
      created_by: 3,
      created_at: timestamp,
    };
  });
}

function buildAlerts(transactions) {
  const suspicious = transactions.filter((t) => t.status === "fraudulent" || t.status === "under_review");
  return suspicious.map((t, i) => {
    // Une transaction déjà tranchée correspond à une alerte confirmée.
    const status = t.status === "fraudulent" ? pick(["confirmed", "confirmed", "open"]) : pick(["open", "open", "rejected"]);
    return {
      id: i + 1,
      prediction: t.id,
      transaction: t.id,
      assigned_to: status === "open" ? null : 2,
      status,
      severity: severityFor(t.fraud_probability),
      comment: "",
      created_at: t.timestamp,
      resolved_at: status === "open" ? null : new Date().toISOString(),
    };
  });
}

export const transactions = buildTransactions(137);
export const alerts = buildAlerts(transactions);
export const reports = [
  {
    id: 1,
    title: "Rapport de septembre",
    type: "pdf",
    generated_by: 1,
    period_start: "2026-09-01",
    period_end: "2026-09-30",
    file_path: "reports/rapport_1.pdf",
    download_url: "/api/reports/1/download/",
    created_at: "2026-10-01T08:00:00Z",
  },
];
