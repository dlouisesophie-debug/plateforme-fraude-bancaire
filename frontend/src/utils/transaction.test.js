import { presetDate, scoringInfo } from "./transaction";

describe("presetDate", () => {
  // Heures locales : le test ne dépend pas du fuseau de la machine.
  const exemple = new Date(2026, 9, 11, 23, 30).toISOString(); // exemple « suspect », 23 h 30

  test("garde l'heure de l'exemple et prend la date du jour si l'heure est passée", () => {
    const maintenant = new Date(2026, 10, 23, 23, 45);
    const d = presetDate(exemple, maintenant);
    expect([d.getFullYear(), d.getMonth(), d.getDate(), d.getHours(), d.getMinutes()]).toEqual([2026, 10, 23, 23, 30]);
  });

  test("prend la veille si l'heure n'est pas encore passée (jamais dans le futur)", () => {
    const maintenant = new Date(2026, 10, 23, 10, 0);
    const d = presetDate(exemple, maintenant);
    expect([d.getDate(), d.getHours(), d.getMinutes()]).toEqual([22, 23, 30]);
    expect(d.getTime()).toBeLessThanOrEqual(maintenant.getTime());
  });
});

describe("scoringInfo", () => {
  test("lit le seuil de décision renvoyé par l'API", () => {
    const info = scoringInfo({ fraud_probability: 0.36, is_fraud_predicted: true, decision_threshold: 0.0652 });
    expect(info).toMatchObject({ probability: 0.36, isFraud: true, threshold: 0.0652 });
  });

  test("transaction non scorée", () => {
    expect(scoringInfo({})).toMatchObject({ probability: null, isFraud: null, threshold: null });
  });
});
