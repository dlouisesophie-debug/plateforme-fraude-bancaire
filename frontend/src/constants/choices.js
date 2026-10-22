export const TRANSACTION_STATUS_CHOICES = [
  { value: "pending", label: "En attente" },
  { value: "legitimate", label: "Légitime" },
  { value: "fraudulent", label: "Frauduleuse" },
  { value: "under_review", label: "En cours d'examen" },
];

export const CHANNEL_CHOICES = [
  { value: "card", label: "Carte" },
  { value: "mobile_money", label: "Mobile Money" },
  { value: "transfer", label: "Virement" },
  { value: "online", label: "Paiement en ligne" },
];

export const ALERT_STATUS_CHOICES = [
  { value: "open", label: "Ouverte" },
  { value: "confirmed", label: "Fraude confirmée" },
  { value: "rejected", label: "Rejetée" },
  { value: "resolved", label: "Résolue" },
];

export const SEVERITY_CHOICES = [
  { value: "low", label: "Faible" },
  { value: "medium", label: "Moyenne" },
  { value: "high", label: "Élevée" },
  { value: "critical", label: "Critique" },
];

export const ROLE_CHOICES = [
  { value: "admin", label: "Administrateur" },
  { value: "analyst", label: "Analyste Fraude" },
  { value: "agent", label: "Agent Financier" },
];

export const GENDER_CHOICES = [
  { value: "F", label: "Femme" },
  { value: "M", label: "Homme" },
];

export const ALGORITHM_CHOICES = [
  { value: "logistic_regression", label: "Régression logistique" },
  { value: "random_forest", label: "Random Forest" },
  { value: "xgboost", label: "XGBoost" },
];

export const REPORT_TYPE_CHOICES = [
  { value: "pdf", label: "PDF" },
  { value: "csv", label: "CSV" },
];

// Catégories et régions connues du pipeline ML (pipeline["categories_connues"]
// et pipeline["regions_connues"]) : une valeur hors liste est ignorée par le modèle.
export const CATEGORY_CHOICES = [
  { value: "achats", label: "Achats" },
  { value: "achats_en_ligne", label: "Achats en ligne" },
  { value: "auto_transport", label: "Auto / Transport" },
  { value: "courses", label: "Courses" },
  { value: "courses_en_ligne", label: "Courses en ligne" },
  { value: "divers", label: "Divers" },
  { value: "divers_en_ligne", label: "Divers en ligne" },
  { value: "divertissement", label: "Divertissement" },
  { value: "enfants_animaux", label: "Enfants / Animaux" },
  { value: "maison", label: "Maison" },
  { value: "restauration", label: "Restauration" },
  { value: "sante_sport", label: "Santé / Sport" },
  { value: "soins_personnels", label: "Soins personnels" },
  { value: "voyage", label: "Voyage" },
];

export const REGION_CHOICES = [
  "Dakar",
  "Diourbel",
  "Fatick",
  "Kaolack",
  "Kolda",
  "Louga",
  "Matam",
  "Saint-Louis",
  "Sédhiou",
  "Tambacounda",
  "Thiès",
  "Ziguinchor",
].map((r) => ({ value: r, label: r }));

export function labelFor(choices, value) {
  return choices.find((c) => c.value === value)?.label ?? value;
}
