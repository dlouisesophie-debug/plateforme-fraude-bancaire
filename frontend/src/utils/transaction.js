// Lit les informations de scoring d'une transaction renvoyée par l'API.
// Les champs sont à plat (fraud_probability, model_version, alert_id,
// alert_status) ; on tolère aussi un objet "prediction" imbriqué.
export function scoringInfo(transaction) {
  const prediction = transaction?.prediction && typeof transaction.prediction === "object" ? transaction.prediction : {};
  return {
    probability: transaction?.fraud_probability ?? prediction.fraud_probability ?? null,
    modelVersion: transaction?.model_version ?? prediction.model_version ?? null,
    isFraud: transaction?.is_fraud ?? prediction.prediction ?? null,
    alertId: transaction?.alert_id ?? null,
    alertStatus: transaction?.alert_status ?? null,
  };
}

// Libellés des champs affichés sur la fiche transaction (ordre d'affichage).
export const TRANSACTION_FIELD_GROUPS = [
  {
    title: "Transaction",
    fields: [
      ["transaction_id", "Identifiant"],
      ["amount", "Montant"],
      ["channel", "Canal"],
      ["timestamp", "Date"],
      ["merchant", "Commerçant"],
      ["category", "Catégorie"],
      ["device", "Appareil"],
      ["location", "Lieu"],
      ["merchant_latitude", "Latitude commerçant"],
      ["merchant_longitude", "Longitude commerçant"],
    ],
  },
  {
    title: "Client",
    fields: [
      ["customer_gender", "Genre"],
      ["customer_birth_date", "Date de naissance"],
      ["customer_profession", "Profession"],
      ["customer_city", "Ville"],
      ["customer_region", "Région"],
      ["customer_city_population", "Population de la ville"],
      ["customer_latitude", "Latitude client"],
      ["customer_longitude", "Longitude client"],
    ],
  },
  {
    title: "Traçabilité",
    fields: [
      ["created_by", "Saisie par"],
      ["created_at", "Enregistrée le"],
    ],
  },
];
