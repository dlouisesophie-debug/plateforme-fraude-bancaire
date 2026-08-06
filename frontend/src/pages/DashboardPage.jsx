import { useEffect, useState } from "react";
import api from "../services/api";

// TODO Etudiant 3 : remplacer par de vrais KPIs et des graphiques Recharts
// (volume total, taux de fraude, montant a risque, alertes actives —
// cf. CDC 5.4).
export default function DashboardPage() {
  const [transactionCount, setTransactionCount] = useState(null);

  useEffect(() => {
    api.get("/transactions/").then((res) => setTransactionCount(res.data.count));
  }, []);

  return (
    <div className="container mt-4">
      <h1 className="h3">Dashboard</h1>
      <div className="card" style={{ maxWidth: 300 }}>
        <div className="card-body">
          <h5 className="card-title">Transactions</h5>
          <p className="card-text fs-4">{transactionCount ?? "..."}</p>
        </div>
      </div>
    </div>
  );
}
