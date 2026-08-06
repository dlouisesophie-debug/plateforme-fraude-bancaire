import { useEffect, useState } from "react";
import api from "../services/api";

// TODO Etudiant 3 : pagination, filtres par statut/canal (CDC 5.2)
export default function TransactionsPage() {
  const [transactions, setTransactions] = useState([]);

  useEffect(() => {
    api.get("/transactions/").then((res) => setTransactions(res.data.results || []));
  }, []);

  return (
    <div className="container mt-4">
      <h1 className="h3">Transactions</h1>
      <table className="table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Montant</th>
            <th>Canal</th>
            <th>Statut</th>
          </tr>
        </thead>
        <tbody>
          {transactions.map((t) => (
            <tr key={t.id}>
              <td>{t.transaction_id}</td>
              <td>{t.amount}</td>
              <td>{t.channel}</td>
              <td>{t.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
