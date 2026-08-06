import { useEffect, useState } from "react";
import api from "../services/api";

// TODO Etudiant 3 : boutons confirmer/rejeter branches sur
// /api/alerts/{id}/confirm/ et /api/alerts/{id}/reject/
export default function AlertsPage() {
  const [alerts, setAlerts] = useState([]);

  useEffect(() => {
    api.get("/alerts/").then((res) => setAlerts(res.data.results || []));
  }, []);

  return (
    <div className="container mt-4">
      <h1 className="h3">Alertes</h1>
      <ul className="list-group">
        {alerts.map((a) => (
          <li key={a.id} className="list-group-item d-flex justify-content-between">
            <span>Alerte #{a.id} — {a.severity}</span>
            <span className="badge bg-warning text-dark">{a.status}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
