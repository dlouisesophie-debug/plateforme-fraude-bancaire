export const TRANSACTION_STATUS_CHOICES = [
  { value: "pending", label: "En attente" },
  { value: "legitimate", label: "Legitime" },
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
  { value: "confirmed", label: "Fraude confirmee" },
  { value: "rejected", label: "Rejetee" },
  { value: "resolved", label: "Resolue" },
];

export const SEVERITY_CHOICES = [
  { value: "low", label: "Faible" },
  { value: "medium", label: "Moyenne" },
  { value: "high", label: "Elevee" },
  { value: "critical", label: "Critique" },
];

export function labelFor(choices, value) {
  return choices.find((c) => c.value === value)?.label ?? value;
}
