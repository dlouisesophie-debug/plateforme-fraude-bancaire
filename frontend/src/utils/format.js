const integerFormatter = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 });
const numberFormatter = new Intl.NumberFormat("fr-FR");
const percentFormatter = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 1 });
const dateFormatter = new Intl.DateTimeFormat("fr-FR", { dateStyle: "short" });
const dateTimeFormatter = new Intl.DateTimeFormat("fr-FR", { dateStyle: "short", timeStyle: "short" });

function isMissing(value) {
  return value === null || value === undefined || value === "";
}

// "640000.00" -> "640 000 FCFA"
export function formatAmount(value) {
  if (isMissing(value) || Number.isNaN(Number(value))) return "—";
  return `${integerFormatter.format(Number(value))} FCFA`;
}

export function formatNumber(value) {
  if (isMissing(value)) return "—";
  return numberFormatter.format(Number(value));
}

// Probabilité 0..1 -> "87,3 %"
export function formatProbability(value) {
  if (isMissing(value)) return "—";
  return `${percentFormatter.format(Number(value) * 100)} %`;
}

// Taux déjà exprimé en pourcentage -> "4,2 %"
export function formatPercent(value) {
  if (isMissing(value)) return "—";
  return `${percentFormatter.format(Number(value))} %`;
}

export function formatDate(value) {
  if (isMissing(value)) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : dateFormatter.format(date);
}

export function formatDateTime(value) {
  if (isMissing(value)) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : dateTimeFormatter.format(date);
}

// Valeur attendue par <input type="datetime-local"> (heure locale).
export function toDateTimeLocal(value) {
  const date = value ? new Date(value) : new Date();
  const pad = (n) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

export function displayName(user) {
  if (!user) return "";
  const fullName = [user.first_name, user.last_name].filter(Boolean).join(" ");
  return fullName || user.username || "";
}

// Réponses DRF : liste brute ou page { count, results }.
export function asList(data) {
  if (Array.isArray(data)) return data;
  return data?.results ?? [];
}

// Transforme une erreur DRF ({ champ: ["msg"] } ou { detail }) en texte lisible.
export function apiErrorMessage(err, fallback) {
  if (!err?.response) return "Serveur injoignable. Vérifiez que le backend est démarré.";
  const data = err.response.data;
  if (data && typeof data === "object" && !(data instanceof Blob)) {
    if (data.detail) return String(data.detail);
    const messages = Object.entries(data).map(([field, value]) => {
      const text = Array.isArray(value) ? value.join(" ") : String(value);
      return field === "non_field_errors" ? text : `${field} : ${text}`;
    });
    if (messages.length) return messages.join(" — ");
  }
  return fallback ?? `Erreur serveur (${err.response.status})`;
}

// "1.0.0" -> "v1.0.0" ; "v1" reste "v1" (le backend peut déjà inclure le préfixe).
export function formatVersion(version) {
  if (version === null || version === undefined || version === "") return "—";
  return /^v/i.test(String(version)) ? String(version) : `v${version}`;
}
