/**
 * Donnees mockees — respectent EXACTEMENT les noms de champs des
 * serializers Django (voir backend, dossier serializers.py de chaque app).
 *
 * Objectif : quand le backend sera pret, il suffira de repointer
 * REACT_APP_USE_MOCKS=false dans .env, sans toucher aux composants.
 *
 * IMPORTANT pour Etudiant 1 (backend) : si un nom de champ change cote
 * serializer, mettez a jour ce fichier en meme temps pour eviter toute
 * divergence silencieuse.
 */

export const mockUser = {
  id: 1,
  username: "fatou.ndoye",
  email: "fatou.ndoye@fraudguard.sn",
  first_name: "Fatou",
  last_name: "Ndoye",
  role: "analyst", // admin | analyst | agent
  is_active: true,
};

export const mockTransactions = [
  {
    id: 1,
    transaction_id: "TX-88213",
    amount: "1250000.00",
    merchant: "Global Import SARL",
    device: "Inconnu (nouveau)",
    location: "Abidjan, CI",
    channel: "transfer", // card | mobile_money | transfer | online
    timestamp: "2026-08-09T14:32:00Z",
    status: "fraudulent", // pending | legitimate | fraudulent | under_review
    created_by: 3,
  },
  {
    id: 2,
    transaction_id: "TX-88212",
    amount: "45000.00",
    merchant: "Boutique Kadi",
    device: "iPhone 14 — habituel",
    location: "Dakar, SN",
    channel: "card",
    timestamp: "2026-08-09T14:20:00Z",
    status: "legitimate",
    created_by: 3,
  },
  {
    id: 3,
    transaction_id: "TX-88211",
    amount: "340000.00",
    merchant: "Orange Money",
    device: "Samsung A54 — habituel",
    location: "Dakar, SN",
    channel: "mobile_money",
    timestamp: "2026-08-09T13:58:00Z",
    status: "under_review",
    created_by: 3,
  },
  {
    id: 4,
    transaction_id: "TX-88210",
    amount: "12800.00",
    merchant: "Pharmacie du Plateau",
    device: "iPhone 13 — habituel",
    location: "Dakar, SN",
    channel: "card",
    timestamp: "2026-08-09T13:41:00Z",
    status: "legitimate",
    created_by: 3,
  },
  {
    id: 5,
    transaction_id: "TX-88209",
    amount: "92500.00",
    merchant: "Wave Transfer",
    device: "Samsung A54 — habituel",
    location: "Thiès, SN",
    channel: "mobile_money",
    timestamp: "2026-08-09T13:15:00Z",
    status: "pending",
    created_by: 3,
  },
];

export const mockPredictions = [
  {
    id: 1,
    transaction: 1,
    ml_model: 1,
    fraud_probability: 0.92,
    prediction: true,
    prediction_date: "2026-08-09T14:32:05Z",
  },
  {
    id: 2,
    transaction: 3,
    ml_model: 1,
    fraud_probability: 0.55,
    prediction: false,
    prediction_date: "2026-08-09T13:58:04Z",
  },
];

export const mockAlerts = [
  {
    id: 1,
    prediction: 1,
    assigned_to: null,
    status: "open", // open | confirmed | rejected | resolved
    severity: "critical", // low | medium | high | critical
    comment: "",
    created_at: "2026-08-09T14:32:10Z",
    resolved_at: null,
    // Champs derives ajoutes cote front pour l'affichage (a exposer
    // eventuellement via un serializer imbrique cote backend) :
    transaction: mockTransactions[0],
    fraud_probability: 0.92,
  },
  {
    id: 2,
    prediction: 3,
    assigned_to: 1,
    status: "open",
    severity: "high",
    comment: "",
    created_at: "2026-08-09T14:20:00Z",
    resolved_at: null,
    transaction: mockTransactions[1],
    fraud_probability: 0.78,
  },
  {
    id: 3,
    prediction: 2,
    assigned_to: 1,
    status: "open",
    severity: "medium",
    comment: "",
    created_at: "2026-08-09T13:58:04Z",
    resolved_at: null,
    transaction: mockTransactions[2],
    fraud_probability: 0.55,
  },
];

export const mockDashboardKpis = {
  transaction_volume: 12480,
  transaction_volume_delta: 4.2,
  fraud_rate: 2.3,
  fraud_rate_delta: 0.8,
  amount_at_risk: 48200000,
  amount_at_risk_delta: -2.1,
  active_alerts: 7,
  active_alerts_delta: 3,
  channel_breakdown: [
    { channel: "card", label: "Carte", percent: 60 },
    { channel: "mobile_money", label: "Mobile Money", percent: 24 },
    { channel: "transfer", label: "Virement", percent: 16 },
  ],
  weekly_volume: [
    { day: "Lun", value: 60 },
    { day: "Mar", value: 45 },
    { day: "Mer", value: 52 },
    { day: "Jeu", value: 70 },
    { day: "Ven", value: 38 },
    { day: "Sam", value: 30 },
    { day: "Dim", value: 25 },
  ],
};

// Simule la latence reseau pour des transitions de chargement realistes
export function delay(data, ms = 400) {
  return new Promise((resolve) => setTimeout(() => resolve(data), ms));
}
