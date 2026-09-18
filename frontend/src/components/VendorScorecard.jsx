export default function VendorScorecard({ vendor, scoreResult, onRunScoring, scoring }) {
  const tier = scoreResult?.final_risk_tier ?? vendor.final_risk_tier;
  const score = scoreResult?.final_risk_score ?? vendor.final_risk_score;
  const mlPrior = scoreResult?.ml_prior_risk_prob ?? vendor.ml_prior_risk_prob;

  return (
    <div className="scorecard">
      <div className="scorecard-header">
        <h2 style={{ margin: 0 }}>{vendor.name}</h2>
        {tier && <span className={`tier-pill tier-${tier}`}>{tier} risk</span>}
      </div>
      <p style={{ color: "var(--muted)" }}>
        {vendor.industry} · {vendor.geography.toUpperCase()} · {vendor.past_incidents} past incident(s)
      </p>

      {score != null ? (
        <>
          <div style={{ display: "flex", gap: 40, marginTop: 16 }}>
            <div>
              <div className="score-big">{Math.round(score * 100)}%</div>
              <div style={{ color: "var(--muted)", fontSize: "0.8rem" }}>Final blended risk score</div>
            </div>
            <div>
              <div style={{ fontSize: "1.4rem", fontWeight: 700 }}>{Math.round(mlPrior * 100)}%</div>
              <div style={{ color: "var(--muted)", fontSize: "0.8rem" }}>
                ML prior (structured attributes only)
              </div>
            </div>
          </div>
          <p style={{ color: "var(--muted)", fontSize: "0.85rem", marginTop: 12 }}>
            The ML model provides the prior from vendor attributes; the agent adjusts it only when a
            grounded (citation-verified) finding confirms a documented issue.
          </p>
        </>
      ) : (
        <p style={{ color: "var(--muted)" }}>Not scored yet.</p>
      )}

      <button className="primary" disabled={scoring} onClick={onRunScoring}>
        {scoring ? "Running agent…" : score != null ? "Re-run assessment" : "Run risk assessment"}
      </button>
    </div>
  );
}
