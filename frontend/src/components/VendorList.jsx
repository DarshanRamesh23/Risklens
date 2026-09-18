export default function VendorList({ vendors, selectedId, onSelect }) {
  return (
    <div>
      {vendors.length === 0 && (
        <div className="empty-state">No vendors yet. Add one to get started.</div>
      )}
      {vendors.map((v) => (
        <div
          key={v.id}
          className={`vendor-card ${v.id === selectedId ? "selected" : ""}`}
          onClick={() => onSelect(v.id)}
        >
          <div className="name">{v.name}</div>
          <div className="meta">
            {v.industry} · {v.geography.toUpperCase()}
          </div>
          {v.final_risk_tier && (
            <div className={`tier-pill tier-${v.final_risk_tier}`}>{v.final_risk_tier} risk</div>
          )}
        </div>
      ))}
    </div>
  );
}
