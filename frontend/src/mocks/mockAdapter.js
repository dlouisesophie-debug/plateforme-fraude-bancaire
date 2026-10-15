// Adaptateur axios qui simule l'API Django en memoire (aucun appel reseau).
// Active via REACT_APP_USE_MOCKS=true dans frontend/.env.
import { AxiosError } from "axios";
import { MOCK_USERS, alerts, transactions } from "./mockData";

const PAGE_SIZE = 20;
const LATENCY_MS = 300;

function respond(config, status, data) {
  const response = { data, status, statusText: String(status), headers: {}, config, request: {} };
  if (status >= 400) {
    throw new AxiosError(`Request failed with status code ${status}`, AxiosError.ERR_BAD_REQUEST, config, {}, response);
  }
  return response;
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

function fakeToken(user) {
  return `mock.${btoa(encodeURIComponent(JSON.stringify({ user_id: user.id, username: user.username })))}.${Date.now()}`;
}

function handle(config) {
  const { method, path, params, body } = parseRequest(config);
  let match;

  if (method === "post" && path === "/auth/login/") {
    // Mode demo : tout couple nom / mot de passe non vide est accepte.
    if (!body.username || !body.password) {
      return respond(config, 401, { detail: "Aucun compte actif n'a ete trouve avec les identifiants fournis" });
    }
    const user = MOCK_USERS.find((u) => u.username === body.username) || { id: 99, username: body.username };
    return respond(config, 200, { access: fakeToken(user), refresh: fakeToken(user) });
  }

  if (method === "post" && path === "/auth/refresh/") {
    return respond(config, 200, { access: fakeToken(MOCK_USERS[0]) });
  }

  if (method === "get" && path === "/transactions/") {
    return respond(config, 200, paginate(filterBy(transactions, params, ["status", "channel"]), path, params));
  }

  if (method === "get" && (match = path.match(/^\/transactions\/(\d+)\/$/))) {
    const transaction = transactions.find((t) => t.id === Number(match[1]));
    return transaction ? respond(config, 200, transaction) : respond(config, 404, { detail: "Pas trouve." });
  }

  if (method === "get" && path === "/alerts/") {
    return respond(config, 200, paginate(filterBy(alerts, params, ["status", "severity"]), path, params));
  }

  if (method === "post" && (match = path.match(/^\/alerts\/(\d+)\/(confirm|reject)\/$/))) {
    const alert = alerts.find((a) => a.id === Number(match[1]));
    if (!alert) return respond(config, 404, { detail: "Pas trouve." });
    alert.status = match[2] === "confirm" ? "confirmed" : "rejected";
    alert.resolved_at = new Date().toISOString();
    alert.assigned_to = MOCK_USERS[0].id;
    return respond(config, 200, { ...alert });
  }

  return respond(config, 404, { detail: `Route non simulee : ${method.toUpperCase()} ${path}` });
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
