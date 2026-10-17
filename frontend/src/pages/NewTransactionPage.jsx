import { useState } from "react";
import { Link } from "react-router-dom";
import api from "../services/api";
import Layout from "../components/Layout";
import ScorePanel from "../components/ScorePanel";
import Notice from "../components/Notice";
import {
  CATEGORY_CHOICES,
  CHANNEL_CHOICES,
  GENDER_CHOICES,
  REGION_CHOICES,
} from "../constants/choices";
import { CARD_CLASS, INPUT_CLASS, LABEL_CLASS, PRIMARY_BUTTON, SECONDARY_BUTTON } from "../constants/ui";
import { apiErrorMessage, formatAmount, toDateTimeLocal } from "../utils/format";
import { scoringInfo } from "../utils/transaction";

function newTransactionId() {
  return `TXN-${Date.now().toString().slice(-8)}`;
}

function emptyForm() {
  return {
    transaction_id: newTransactionId(),
    amount: "",
    channel: "card",
    timestamp: toDateTimeLocal(),
    merchant: "",
    category: "",
    device: "",
    location: "",
    merchant_latitude: "",
    merchant_longitude: "",
    customer_gender: "",
    customer_birth_date: "",
    customer_profession: "",
    customer_city: "",
    customer_region: "",
    customer_city_population: "",
    customer_latitude: "",
    customer_longitude: "",
  };
}

// Jeux de démonstration repris de backend/fraud_detection/sample_transactions.py
// (valeurs vérifiées sur le vrai pipeline ML).
const PRESETS = {
  normal: {
    amount: "15000",
    merchant: "fraud_Kilback LLC",
    device: "mobile",
    location: "Dakar",
    channel: "card",
    timestamp: "2026-10-11T14:30:00Z",
    category: "achats",
    customer_gender: "F",
    customer_birth_date: "1995-03-20",
    customer_city: "Dakar",
    customer_region: "Dakar",
    customer_city_population: "1200000",
    customer_profession: "Ingénieure",
    customer_latitude: "14.6928",
    customer_longitude: "-17.4467",
    merchant_latitude: "14.7167",
    merchant_longitude: "-17.4677",
  },
  suspect: {
    amount: "600000",
    merchant: "fraud_Wilkinson LLC",
    device: "web",
    location: "Richard-Toll",
    channel: "online",
    timestamp: "2026-10-11T23:30:00Z",
    category: "courses",
    customer_gender: "M",
    customer_birth_date: "1963-05-02",
    customer_city: "Richard-Toll",
    customer_region: "Fatick",
    customer_city_population: "50000",
    customer_profession: "Geoscientist",
    customer_latitude: "15.51034618905701",
    customer_longitude: "-13.76961263585134",
    merchant_latitude: "14.898403094975828",
    merchant_longitude: "-14.017604647296018",
  },
};

const NUMBER_FIELDS = [
  "amount",
  "customer_city_population",
  "customer_latitude",
  "customer_longitude",
  "merchant_latitude",
  "merchant_longitude",
];

// Les champs vides sont omis : le backend applique alors ses valeurs neutres.
function toPayload(form) {
  const payload = {};
  Object.entries(form).forEach(([key, value]) => {
    if (value === "" || value === null) return;
    if (key === "timestamp") payload[key] = new Date(value).toISOString();
    else if (NUMBER_FIELDS.includes(key)) payload[key] = Number(value);
    else payload[key] = typeof value === "string" ? value.trim() : value;
  });
  return payload;
}

function Field({ label, name, form, onChange, required, children, ...inputProps }) {
  const id = `field-${name}`;
  return (
    <div>
      <label htmlFor={id} className={LABEL_CLASS}>
        {label}
        {required && <span className="text-danger"> *</span>}
      </label>
      {children ? (
        <select id={id} name={name} value={form[name]} onChange={onChange} required={required} className={INPUT_CLASS}>
          {children}
        </select>
      ) : (
        <input
          id={id}
          name={name}
          value={form[name]}
          onChange={onChange}
          required={required}
          className={INPUT_CLASS}
          {...inputProps}
        />
      )}
    </div>
  );
}

function Options({ choices, placeholder }) {
  return (
    <>
      {placeholder && <option value="">{placeholder}</option>}
      {choices.map((c) => (
        <option key={c.value} value={c.value}>
          {c.label}
        </option>
      ))}
    </>
  );
}

export default function NewTransactionPage() {
  const [form, setForm] = useState(emptyForm);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  function handleChange(e) {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  }

  function applyPreset(name) {
    const preset = PRESETS[name];
    setForm({ ...emptyForm(), ...preset, timestamp: toDateTimeLocal(preset.timestamp) });
    setResult(null);
    setError(null);
  }

  function reset() {
    setForm(emptyForm());
    setResult(null);
    setError(null);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    setResult(null);
    try {
      const { data } = await api.post("/transactions/", toPayload(form));
      setResult(data);
    } catch (err) {
      setError(apiErrorMessage(err, "Enregistrement de la transaction impossible."));
    } finally {
      setSubmitting(false);
    }
  }

  const fieldProps = { form, onChange: handleChange };
  const scoring = result ? scoringInfo(result) : null;

  return (
    <Layout>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ink-primary">Nouvelle transaction</h1>
          <p className="mt-1 text-sm text-ink-secondary">
            La transaction est analysée par le modèle IA dès son enregistrement.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={() => applyPreset("normal")} className={SECONDARY_BUTTON}>
            Exemple normal
          </button>
          <button type="button" onClick={() => applyPreset("suspect")} className={SECONDARY_BUTTON}>
            Exemple suspect
          </button>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <form onSubmit={handleSubmit} className="space-y-4 lg:col-span-2">
          <section className={CARD_CLASS}>
            <h2 className="text-sm font-medium text-ink-primary">Transaction</h2>
            <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Field label="Identifiant" name="transaction_id" required {...fieldProps} />
              <Field label="Montant (FCFA)" name="amount" type="number" min="1" step="1" required {...fieldProps} />
              <Field label="Canal" name="channel" required {...fieldProps}>
                <Options choices={CHANNEL_CHOICES} />
              </Field>
              <Field label="Date et heure" name="timestamp" type="datetime-local" required {...fieldProps} />
              <Field label="Commerçant" name="merchant" {...fieldProps} />
              <Field label="Catégorie" name="category" {...fieldProps}>
                <Options choices={CATEGORY_CHOICES} placeholder="— Choisir —" />
              </Field>
              <Field label="Appareil" name="device" placeholder="mobile, web, TPE..." {...fieldProps} />
              <Field label="Lieu" name="location" {...fieldProps} />
              <Field label="Latitude commerçant" name="merchant_latitude" type="number" step="any" {...fieldProps} />
              <Field label="Longitude commerçant" name="merchant_longitude" type="number" step="any" {...fieldProps} />
            </div>
          </section>

          <section className={CARD_CLASS}>
            <h2 className="text-sm font-medium text-ink-primary">Client</h2>
            <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Field label="Genre" name="customer_gender" {...fieldProps}>
                <Options choices={GENDER_CHOICES} placeholder="— Choisir —" />
              </Field>
              <Field label="Date de naissance" name="customer_birth_date" type="date" {...fieldProps} />
              <Field label="Profession" name="customer_profession" {...fieldProps} />
              <Field label="Ville" name="customer_city" {...fieldProps} />
              <Field label="Région" name="customer_region" {...fieldProps}>
                <Options choices={REGION_CHOICES} placeholder="— Choisir —" />
              </Field>
              <Field label="Population de la ville" name="customer_city_population" type="number" min="0" step="1" {...fieldProps} />
              <Field label="Latitude client" name="customer_latitude" type="number" step="any" {...fieldProps} />
              <Field label="Longitude client" name="customer_longitude" type="number" step="any" {...fieldProps} />
            </div>
          </section>

          <Notice>{error}</Notice>

          <div className="flex flex-wrap gap-2">
            <button type="submit" disabled={submitting} className={PRIMARY_BUTTON}>
              {submitting ? "Analyse en cours..." : "Enregistrer et analyser"}
            </button>
            <button type="button" onClick={reset} className={SECONDARY_BUTTON}>
              Réinitialiser
            </button>
          </div>
        </form>

        <aside className="lg:sticky lg:top-6 lg:self-start" aria-live="polite">
          {result ? (
            <div className="space-y-3">
              <ScorePanel transaction={result} />
              <Notice tone={scoring.alertId ? "danger" : "success"}>
                {scoring.alertId
                  ? `Alerte #${scoring.alertId} créée : la transaction ${result.transaction_id} (${formatAmount(result.amount)}) est transmise aux analystes.`
                  : `Transaction ${result.transaction_id} enregistrée, aucune alerte déclenchée.`}
              </Notice>
              <div className="flex flex-wrap gap-2">
                {result.id && (
                  <Link to={`/transactions/${result.id}`} className={SECONDARY_BUTTON}>
                    Voir la fiche
                  </Link>
                )}
                <button type="button" onClick={reset} className={PRIMARY_BUTTON}>
                  Nouvelle saisie
                </button>
              </div>
            </div>
          ) : (
            <div className={`${CARD_CLASS} text-sm text-ink-secondary`}>
              <p className="text-xs font-medium uppercase tracking-wide">Score de fraude</p>
              <p className="mt-3">
                {submitting
                  ? "Le modèle analyse la transaction..."
                  : "Le score s'affichera ici après l'enregistrement."}
              </p>
            </div>
          )}
        </aside>
      </div>
    </Layout>
  );
}
