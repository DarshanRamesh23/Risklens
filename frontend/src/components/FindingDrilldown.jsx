import { useState } from "react";

export default function FindingDrilldown({ findings }) {
  const [expandedId, setExpandedId] = useState(null);

  if (!findings || findings.length === 0) {
    return <div className="empty-state">No findings yet. Run an assessment to generate some.</div>;
  }

  return (
    <div>
      <h3>Findings — why was this flagged?</h3>
      {findings.map((f) => {
        const expanded = expandedId === f.id;
        return (
          <div
            key={f.id}
            className={`finding-row ${expanded ? "expanded" : ""}`}
            onClick={() => setExpandedId(expanded ? null : f.id)}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <span className={`tier-pill tier-${f.severity}`}>{f.severity}</span>{" "}
                <strong>{f.summary}</strong>
              </div>
              <span className={`grounded-badge grounded-${f.grounded}`}>
                {f.grounded ? "Citation verified" : "Ungrounded — needs review"}
              </span>
            </div>

            {expanded && (
              <>
                <div className="quote-block">
                  <strong>Vendor document says:</strong> "{f.vendor_quote}"
                </div>
                <div className="quote-block">
                  <strong>Matched policy clause:</strong> "{f.policy_quote}"
                </div>
              </>
            )}
          </div>
        );
      })}
    </div>
  );
}
