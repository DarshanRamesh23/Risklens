import { useEffect, useState } from "react";
import { api } from "./api";
import VendorList from "./components/VendorList";
import VendorScorecard from "./components/VendorScorecard";
import FindingDrilldown from "./components/FindingDrilldown";

export default function App() {
  const [vendors, setVendors] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [findings, setFindings] = useState([]);
  const [scoreResult, setScoreResult] = useState(null);
  const [scoring, setScoring] = useState(false);
  const [error, setError] = useState(null);

  const refreshVendors = () => api.listVendors().then(setVendors).catch((e) => setError(e.message));

  useEffect(() => {
    refreshVendors();
  }, []);

  useEffect(() => {
    if (selectedId == null) return;
    setScoreResult(null);
    api
      .getVendorFindings(selectedId)
      .then(setFindings)
      .catch((e) => setError(e.message));
  }, [selectedId]);

  const selectedVendor = vendors.find((v) => v.id === selectedId);

  async function handleRunScoring() {
    setScoring(true);
    setError(null);
    try {
      const result = await api.scoreVendor(selectedId);
      setScoreResult(result);
      setFindings(result.findings);
      refreshVendors();
    } catch (e) {
      setError(e.message);
    } finally {
      setScoring(false);
    }
  }

  return (
    <div className="app-shell">
      <div className="sidebar">
        <div className="brand">RiskLens</div>
        <div className="brand-sub">Third-Party Risk Copilot</div>
        <VendorList vendors={vendors} selectedId={selectedId} onSelect={setSelectedId} />
      </div>

      <div className="main">
        {error && (
          <div style={{ color: "var(--high)", marginBottom: 16 }}>
            {error} — is the backend running on :8000?
          </div>
        )}

        {!selectedVendor ? (
          <div className="empty-state">Select a vendor to view its risk assessment.</div>
        ) : (
          <>
            <VendorScorecard
              vendor={selectedVendor}
              scoreResult={scoreResult}
              onRunScoring={handleRunScoring}
              scoring={scoring}
            />
            <FindingDrilldown findings={findings} />
          </>
        )}
      </div>
    </div>
  );
}
