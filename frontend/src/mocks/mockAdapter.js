// Adaptateur axios qui simule l'API Django en mémoire (aucun appel réseau).
// Activé via REACT_APP_USE_MOCKS=true dans frontend/.env.
import { AxiosError } from "axios";
import {
  ACTIVE_MODEL_VERSION,
  DECISION_THRESHOLD,
  MOCK_USERS,
  alerts,
  mlModels,
  reports,
  severityFor,
  transactions,
} from "./mockData";

const PAGE_SIZE = 20;
const LATENCY_MS = 300;

function respond(config, status, data, headers = {}) {
  const response = { data, status, statusText: String(status), headers, config, request: {} };
  if (status >= 400) {
    throw new AxiosError(`Request failed with status code ${status}`, AxiosError.ERR_BAD_REQUEST, config, {}, response);
  }
  return response;
}

function respondFile(config, content, type, filename) {
  return respond(config, 200, new Blob([content], { type }), {
    "content-type": type,
    "content-disposition": `attachment; filename="${filename}"`,
  });
}

function parseRequest(config) {
  const url = new URL(config.url, "http://mock");
  const params = Object.fromEntries(url.searchParams);
  Object.entries(config.params || {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") params[key] = String(value);
  });
  const path = url.pathname.replace(/^\/api/, "").replace(/\/?$/, "/");
  const body = typeof config.data === "string" ? JSON.parse(config.data || "{}") : config.data || {};
  return { method: (config.method || "get").toLowerCase(), path, params, body };
}

// Reproduit la pagination DRF : { count, next, previous, results }.
function paginate(items, path, params) {
  const page = Math.max(1, Number(params.page) || 1);
  const start = (page - 1) * PAGE_SIZE;
  const pageUrl = (n) => {
    const search = new URLSearchParams({ ...params, page: String(n) });
    return `${path}?${search.toString()}`;
  };
  return {
    count: items.length,
    next: start + PAGE_SIZE < items.length ? pageUrl(page + 1) : null,
    previous: page > 1 ? pageUrl(page - 1) : null,
    results: items.slice(start, start + PAGE_SIZE),
  };
}

function filterBy(items, params, fields) {
  return items.filter((item) => fields.every((f) => !params[f] || item[f] === params[f]));
}

function filterByPeriod(items, params, field = "timestamp") {
  return items.filter((item) => {
    const day = String(item[field]).slice(0, 10);
    return (!params.date_after || day >= params.date_after) && (!params.date_before || day <= params.date_before);
  });
}

function fakeToken(user) {
  return `mock.${btoa(encodeURIComponent(JSON.stringify({ user_id: user.id, username: user.username })))}.${Date.now()}`;
}

function currentUser(config) {
  const header = config.headers?.Authorization || config.headers?.authorization || "";
  try {
    const payload = JSON.parse(decodeURIComponent(atob(header.split(".")[1])));
    return MOCK_USERS.find((u) => u.id === payload.user_id) || MOCK_USERS[0];
  } catch {
    return MOCK_USERS[0];
  }
}

const alertForTransaction = (t) => alerts.find((a) => a.transaction === t.id);

function serializeTransaction(t) {
  const alert = alertForTransaction(t);
  return {
    ...t,
    is_fraud_predicted: t.fraud_probability === null ? null : t.fraud_probability >= DECISION_THRESHOLD,
    alert_id: alert?.id ?? null,
    alert_status: alert?.status ?? null,
  };
}

function serializeAlert(a) {
  const t = transactions.find((tx) => tx.id === a.transaction) || {};
  return {
    ...a,
    transaction_id: t.transaction_id,
    amount: t.amount,
    channel: t.channel,
    timestamp: t.timestamp,
    fraud_probability: t.fraud_probability,
  };
}

function filteredTransactions(params) {
  const search = (params.search || "").toLowerCase();
  let items = filterBy(transactions, params, ["status", "channel"]);
  items = filterByPeriod(items, params);
  if (search) {
    items = items.filter((t) =>
      [t.transaction_id, t.merchant, t.location, t.customer_city].some((v) => String(v || "").toLowerCase().includes(search))
    );
  }
  return items;
}

// Imite le pipeline ML : gros montant et heure nocturne font monter le score.
function fakeScore(t) {
  const hour = new Date(t.timestamp).getUTCHours();
  const night = hour >= 22 || hour < 6 ? 0.35 : 0;
  const amountPart = Math.min(Number(t.amount) / 700000, 1) * 0.6;
  return Number(Math.min(0.995, amountPart + night + Math.random() * 0.02).toFixed(4));
}

function csvLine(values) {
  return values.map((v) => `"${String(v ?? "").replace(/"/g, '""')}"`).join(";");
}

function transactionsCsv(items) {
  const header = ["transaction_id", "timestamp", "amount", "channel", "merchant", "status", "fraud_probability"];
  return [csvLine(header), ...items.map((t) => csvLine(header.map((h) => t[h])))].join("\n");
}

function dashboardStats(params) {
  const items = filterByPeriod(transactions, params);
  const total = items.length;
  const byStatus = { pending: 0, legitimate: 0, fraudulent: 0, under_review: 0 };
  items.forEach((t) => {
    byStatus[t.status] += 1;
  });

  const dailyMap = {};
  items.forEach((t) => {
    const day = t.timestamp.slice(0, 10);
    dailyMap[day] = dailyMap[day] || { date: day, total: 0, fraudulent: 0 };
    dailyMap[day].total += 1;
    if (t.status === "fraudulent") dailyMap[day].fraudulent += 1;
  });

  const byChannel = ["card", "mobile_money", "transfer", "online"].map((channel) => {
    const subset = items.filter((t) => t.channel === channel);
    return { channel, total: subset.length, fraudulent: subset.filter((t) => t.status === "fraudulent").length };
  });

  // Prédit fraude = score au-dessus du seuil ; réel = décision de l'analyste.
  const decided = items.filter((t) => t.fraud_probability !== null && (t.status === "fraudulent" || t.status === "legitimate"));
  const cm = { tp: 0, fp: 0, tn: 0, fn: 0 };
  decided.forEach((t) => {
    const predicted = t.fraud_probability >= DECISION_THRESHOLD;
    const actual = t.status === "fraudulent";
    if (predicted && actual) cm.tp += 1;
    else if (predicted) cm.fp += 1;
    else if (actual) cm.fn += 1;
    else cm.tn += 1;
  });

  const ids = new Set(items.map((t) => t.id));
  const ratio = (n, d) => (d ? Number((n / d).toFixed(4)) : null);
  const model = mlModels.find((m) => m.is_active);
  // Même forme que backend/dashboard/services.py (calculer_statistiques).
  return {
    filters: { date_after: params.date_after || null, date_before: params.date_before || null, channel: null },
    kpis: {
      total_transactions: total,
      fraudulent_transactions: byStatus.fraudulent,
      fraud_rate: total > 0 ? Number(((byStatus.fraudulent / total) * 100).toFixed(2)) : 0,
      amount_at_risk: items
        .filter((t) => t.status === "fraudulent" || t.status === "under_review")
        .reduce((acc, t) => acc + Number(t.amount), 0),
      active_alerts: alerts.filter((a) => a.status === "open" && ids.has(a.transaction)).length,
    },
    by_status: Object.entries(byStatus).map(([status, count]) => ({ status, count })),
    by_channel: byChannel,
    daily: Object.values(dailyMap).sort((a, b) => a.date.localeCompare(b.date)),
    confusion_matrix: {
      true_positive: cm.tp,
      false_positive: cm.fp,
      false_negative: cm.fn,
      true_negative: cm.tn,
      evaluated: cm.tp + cm.fp + cm.fn + cm.tn,
      precision: ratio(cm.tp, cm.tp + cm.fp),
      recall: ratio(cm.tp, cm.tp + cm.fn),
    },
    active_model: model
      ? {
          version: model.version,
          algorithm: model.algorithm,
          precision: model.precision_score,
          recall: model.recall_score,
          f1_score: model.f1_score,
          auc_roc: model.auc_roc,
          trained_at: model.trained_at,
        }
      : null,
  };
}

function handle(config) {
  const { method, path, params, body } = parseRequest(config);
  let match;

  if (method === "post" && path === "/auth/login/") {
    // Mode démo : tout couple nom / mot de passe non vide est accepté.
    if (!body.username || !body.password) {
      return respond(config, 401, { detail: "Aucun compte actif n'a été trouvé avec les identifiants fournis" });
    }
    const user = MOCK_USERS.find((u) => u.username === body.username) || {
      ...MOCK_USERS[0],
      id: 99,
      username: body.username,
      first_name: "",
      last_name: "",
    };
    if (user.id === 99 && !MOCK_USERS.some((u) => u.id === 99)) MOCK_USERS.push(user);
    return respond(config, 200, { access: fakeToken(user), refresh: fakeToken(user), user });
  }

  if (method === "post" && path === "/auth/refresh/") {
    return respond(config, 200, { access: fakeToken(currentUser(config)) });
  }

  if (method === "get" && path === "/auth/me/") {
    return respond(config, 200, currentUser(config));
  }

  if (method === "get" && path === "/auth/users/") {
    return respond(config, 200, paginate(MOCK_USERS, path, params));
  }

  if (method === "post" && path === "/auth/users/") {
    if (!body.username) return respond(config, 400, { username: ["Ce champ est obligatoire."] });
    if (MOCK_USERS.some((u) => u.username === body.username)) {
      return respond(config, 400, { username: ["Un utilisateur avec ce nom existe déjà."] });
    }
    const { password: _password, ...rest } = body;
    const user = { ...rest, id: Math.max(...MOCK_USERS.map((u) => u.id)) + 1, is_active: true };
    MOCK_USERS.push(user);
    return respond(config, 201, user);
  }

  if (method === "get" && path === "/dashboard/stats/") {
    return respond(config, 200, dashboardStats(params));
  }

  if (method === "get" && path === "/transactions/export/") {
    return respondFile(config, transactionsCsv(filteredTransactions(params)), "text/csv", "transactions.csv");
  }

  if (method === "get" && path === "/transactions/") {
    return respond(config, 200, paginate(filteredTransactions(params).map(serializeTransaction), path, params));
  }

  if (method === "post" && path === "/transactions/") {
    if (transactions.some((t) => t.transaction_id === body.transaction_id)) {
      return respond(config, 400, { transaction_id: ["Une transaction avec cet identifiant existe déjà."] });
    }
    if (!(Number(body.amount) > 0)) {
      return respond(config, 400, { amount: ["Le montant doit être strictement supérieur à 0."] });
    }
    const now = new Date().toISOString();
    const transaction = {
      ...body,
      id: Math.max(...transactions.map((t) => t.id)) + 1,
      amount: Number(body.amount).toFixed(2),
      created_by: currentUser(config).id,
      created_at: now,
    };
    transaction.fraud_probability = fakeScore(transaction);
    transaction.model_version = ACTIVE_MODEL_VERSION;
    const isFraud = transaction.fraud_probability >= DECISION_THRESHOLD;
    transaction.status = isFraud ? "under_review" : "legitimate";
    transactions.unshift(transaction);
    if (isFraud) {
      alerts.unshift({
        id: Math.max(0, ...alerts.map((a) => a.id)) + 1,
        prediction: transaction.id,
        transaction: transaction.id,
        assigned_to: null,
        status: "open",
        severity: severityFor(transaction.fraud_probability),
        comment: "",
        created_at: now,
        resolved_at: null,
      });
    }
    return respond(config, 201, { ...serializeTransaction(transaction), is_fraud_predicted: isFraud });
  }

  if (method === "get" && (match = path.match(/^\/transactions\/(\d+)\/$/))) {
    const transaction = transactions.find((t) => t.id === Number(match[1]));
    return transaction ? respond(config, 200, serializeTransaction(transaction)) : respond(config, 404, { detail: "Pas trouvé." });
  }

  if (method === "get" && path === "/alerts/") {
    return respond(config, 200, paginate(filterBy(alerts, params, ["status", "severity"]).map(serializeAlert), path, params));
  }

  if (method === "post" && (match = path.match(/^\/alerts\/(\d+)\/(confirm|reject)\/$/))) {
    const alert = alerts.find((a) => a.id === Number(match[1]));
    if (!alert) return respond(config, 404, { detail: "Pas trouvé." });
    alert.status = match[2] === "confirm" ? "confirmed" : "rejected";
    alert.resolved_at = new Date().toISOString();
    alert.assigned_to = currentUser(config).id;
    if (body.comment !== undefined) alert.comment = body.comment;
    const transaction = transactions.find((t) => t.id === alert.transaction);
    if (transaction) transaction.status = alert.status === "confirmed" ? "fraudulent" : "legitimate";
    return respond(config, 200, serializeAlert(alert));
  }

  if (method === "patch" && (match = path.match(/^\/alerts\/(\d+)\/$/))) {
    const alert = alerts.find((a) => a.id === Number(match[1]));
    if (!alert) return respond(config, 404, { detail: "Pas trouvé." });
    if (body.comment !== undefined) alert.comment = body.comment;
    return respond(config, 200, serializeAlert(alert));
  }

  if (method === "get" && path === "/fraud-detection/models/") {
    return respond(config, 200, paginate(mlModels, path, params));
  }

  if (method === "get" && path === "/reports/") {
    return respond(config, 200, paginate(reports, path, params));
  }

  if (method === "post" && path === "/reports/") {
    if (!body.title) return respond(config, 400, { title: ["Ce champ est obligatoire."] });
    const id = Math.max(0, ...reports.map((r) => r.id)) + 1;
    const report = {
      ...body,
      id,
      generated_by: currentUser(config).id,
      file_path: `reports/rapport_${id}.${body.type}`,
      download_url: `/api/reports/${id}/download/`,
      created_at: new Date().toISOString(),
    };
    reports.unshift(report);
    return respond(config, 201, report);
  }

  if (method === "get" && (match = path.match(/^\/reports\/(\d+)\/download\/$/))) {
    const report = reports.find((r) => r.id === Number(match[1]));
    if (!report) return respond(config, 404, { detail: "Pas trouvé." });
    const items = filterByPeriod(transactions, { date_after: report.period_start, date_before: report.period_end });
    // En mode mock, le "PDF" est un simple fichier texte : seul le flux est simulé.
    return report.type === "csv"
      ? respondFile(config, transactionsCsv(items), "text/csv", `rapport_${report.id}.csv`)
      : respondFile(config, `${report.title}\n\n${items.length} transactions sur la période.`, "text/plain", `rapport_${report.id}.txt`);
  }

  return respond(config, 404, { detail: `Route non simulée : ${method.toUpperCase()} ${path}` });
}

export default function mockAdapter(config) {
  return new Promise((resolve, reject) => {
    setTimeout(() => {
      try {
        resolve(handle(config));
      } catch (err) {
        reject(err);
      }
    }, LATENCY_MS);
  });
}
