const integerFormatter = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 });
const numberFormatter = new Intl.NumberFormat("fr-FR");
const percentFormatter = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 1 });
const dateFormatter = new Intl.DateTimeFormat("fr-FR", { dateStyle: "short" });
const dateTimeFormatter = new Intl.DateTimeFormat("fr-FR", { dateStyle: "short", timeStyle: "short" });

// Intl (fr-FR) sépare les milliers par une espace fine insécable (U+202F), que certaines
// polices affichent sans largeur (« 1760000 FCFA » sur Mac) : on met une espace insécable (U+00A0).
const espaces = (texte) => texte.replace(/\u202F/g, "\u00A0");

function isMissing(value) {
  return value === null || value === undefined || value === "";
}

// "640000.00" -> "640 000 FCFA"
export function formatAmount(value) {
  if (isMissing(value) || Number.isNaN(Number(value))) return "—";
  return `${espaces(integerFormatter.format(Number(value)))} FCFA`;
}

export function formatNumber(value) {
  if (isMissing(value)) return "—";
  return espaces(numberFormatter.format(Number(value)));
}

// Montant d'une transaction (ou d'une alerte) : en FCFA, sauf en mobile money avec un
// type d'opération, saisi dans l'unité du simulateur PaySim du modèle mobile money.
export function formatTransactionAmount(item) {
  if (!item?.operation_type) return formatAmount(item?.amount);
  if (isMissing(item.amount) || Number.isNaN(Number(item.amount))) return "—";
  return `${espaces(integerFormatter.format(Number(item.amount)))} (unité simulateur)`;
}

// Probabilité 0..1 -> "87,3 %" ; au-delà de 99,95 %, « > 99,9 % » plutôt que « 100 % ».
export function formatProbability(value) {
  if (isMissing(value)) return "—";
  if (Number(value) >= 0.9995) return "> 99,9 %";
  return `${percentFormatter.format(Number(value) * 100)} %`;
}

// Coordonnée GPS -> "14,7167" (virgule décimale, comme dans le formulaire)
export function formatCoordinate(value) {
  if (isMissing(value) || Number.isNaN(Number(value))) return "—";
  return new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 6 }).format(Number(value));
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

// Durée entre deux instants -> "moins d'une minute", "12 min", "2 h 5 min", "3 j 4 h".
// Un léger décalage d'horloge entre serveur et navigateur compte comme une durée nulle.
export function formatDuration(from, to = Date.now()) {
  if (isMissing(from) || isMissing(to)) return null;
  const elapsed = new Date(to).getTime() - new Date(from).getTime();
  if (Number.isNaN(elapsed)) return null;
  const minutes = Math.floor(Math.max(0, elapsed) / 60000);
  if (minutes < 1) return "moins d'une minute";
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return minutes % 60 ? `${hours} h ${minutes % 60} min` : `${hours} h`;
  const days = Math.floor(hours / 24);
  return hours % 24 ? `${days} j ${hours % 24} h` : `${days} j`;
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

// "1.0.0" -> "v1.0.0" ; "v1" et "mm-v1" restent tels quels (préfixe seulement devant un chiffre).
export function formatVersion(version) {
  if (version === null || version === undefined || version === "") return "—";
  return /^\d/.test(String(version)) ? `v${version}` : String(version);
}
