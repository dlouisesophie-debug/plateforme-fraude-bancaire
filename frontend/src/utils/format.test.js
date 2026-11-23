import {
  apiErrorMessage,
  displayName,
  formatAmount,
  formatCoordinate,
  formatDuration,
  formatNumber,
  formatPercent,
  formatProbability,
  formatTransactionAmount,
  formatVersion,
} from "./format";

const NBSP = " ";

describe("formatAmount", () => {
  test("sépare les milliers par une espace insécable visible (pas U+202F)", () => {
    const texte = formatAmount("1760000.00");
    expect(texte).toBe(`1${NBSP}760${NBSP}000 FCFA`);
    expect(texte).not.toMatch(/ /);
  });

  test("valeur absente ou invalide -> tiret", () => {
    expect(formatAmount(null)).toBe("—");
    expect(formatAmount("")).toBe("—");
    expect(formatAmount("abc")).toBe("—");
  });
});

describe("formatNumber", () => {
  test("pas d'espace fine insécable", () => {
    expect(formatNumber(110474)).toBe(`110${NBSP}474`);
  });
});

describe("formatTransactionAmount", () => {
  test("carte : FCFA", () => {
    expect(formatTransactionAmount({ amount: "25000", operation_type: "" })).toBe(`25${NBSP}000 FCFA`);
  });

  test("mobile money avec type d'opération : unité du simulateur, jamais FCFA", () => {
    const texte = formatTransactionAmount({ amount: "181000", operation_type: "cash_out" });
    expect(texte).toBe(`181${NBSP}000 (unité simulateur)`);
    expect(texte).not.toMatch(/FCFA/);
  });
});

describe("formatProbability", () => {
  test("virgule décimale", () => {
    expect(formatProbability(0.873)).toBe("87,3 %");
  });

  test("n'affiche jamais 100 % pour un score qui n'est pas une certitude", () => {
    expect(formatProbability(0.99999)).toBe("> 99,9 %");
    expect(formatProbability(0.9994)).toBe("99,9 %");
  });

  test("valeur absente -> tiret", () => {
    expect(formatProbability(undefined)).toBe("—");
  });
});

describe("formatCoordinate", () => {
  test("virgule décimale, 6 chiffres au plus", () => {
    expect(formatCoordinate("14.716677")).toBe("14,716677");
    expect(formatCoordinate(-17.4677)).toBe("-17,4677");
  });

  test("valeur absente -> tiret", () => {
    expect(formatCoordinate(null)).toBe("—");
  });
});

describe("formatPercent", () => {
  test("taux déjà en pourcentage", () => {
    expect(formatPercent(4.25)).toMatch(/^4,[23] %$/);
  });
});

describe("formatDuration", () => {
  const debut = "2026-11-20T10:00:00Z";
  test.each([
    ["2026-11-20T10:00:30Z", "moins d'une minute"],
    ["2026-11-20T10:12:00Z", "12 min"],
    ["2026-11-20T12:05:00Z", "2 h 5 min"],
    ["2026-11-23T14:00:00Z", "3 j 4 h"],
  ])("jusqu'à %s -> %s", (fin, attendu) => {
    expect(formatDuration(debut, fin)).toBe(attendu);
  });

  test("décalage d'horloge négatif compté comme nul", () => {
    expect(formatDuration(debut, "2026-11-20T09:59:00Z")).toBe("moins d'une minute");
  });
});

describe("formatVersion", () => {
  test("préfixe v seulement devant un chiffre", () => {
    expect(formatVersion("2")).toBe("v2");
    expect(formatVersion("mm-v1")).toBe("mm-v1");
    expect(formatVersion(null)).toBe("—");
  });
});

describe("displayName", () => {
  test("nom complet, sinon identifiant", () => {
    expect(displayName({ first_name: "Awa", last_name: "Ndiaye", username: "awa" })).toBe("Awa Ndiaye");
    expect(displayName({ username: "analyste1" })).toBe("analyste1");
  });
});

describe("apiErrorMessage", () => {
  test("serveur injoignable", () => {
    expect(apiErrorMessage({})).toMatch(/Serveur injoignable/);
  });

  test("erreurs de champ DRF", () => {
    const err = { response: { status: 400, data: { amount: ["Doit être positif."] } } };
    expect(apiErrorMessage(err)).toBe("amount : Doit être positif.");
  });
});
