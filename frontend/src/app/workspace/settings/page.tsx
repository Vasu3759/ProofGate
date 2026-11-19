"use client";

import { useState } from "react";

export default function SettingsPage() {
  const [tenantName, setTenantName] = useState("Meridian Labs");
  const [defaultThreshold, setDefaultThreshold] = useState("85");
  const [failClosed, setFailClosed] = useState(true);
  const [saved, setSaved] = useState(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  };

  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow blue">PLATFORM&nbsp; / &nbsp;08&nbsp; · &nbsp;SETTINGS</div>
          <h1>Workspace settings</h1>
          <p>Tenant policies, compliance scoring thresholds, and governance enforcement preferences.</p>
        </div>
      </div>

      <form onSubmit={handleSave} style={{ maxWidth: "800px", display: "flex", flexDirection: "column", gap: "1.5rem" }}>
        <section className="panel">
          <div className="panel-head">
            <div>
              <div className="eyebrow">ORGANIZATION IDENTITY</div>
              <h2>Tenant profile &amp; slug</h2>
            </div>
          </div>
          <div style={{ padding: "1.25rem", display: "flex", flexDirection: "column", gap: "1rem" }}>
            <label style={{ display: "flex", flexDirection: "column", gap: "0.4rem", fontSize: "0.85rem" }}>
              <span style={{ color: "#aaa" }}>Organization Name</span>
              <input
                type="text"
                value={tenantName}
                onChange={(e) => setTenantName(e.target.value)}
                style={{ padding: "0.5rem 0.75rem", background: "#0a0a0a", border: "1px solid #333", color: "#fff" }}
              />
            </label>
            <label style={{ display: "flex", flexDirection: "column", gap: "0.4rem", fontSize: "0.85rem" }}>
              <span style={{ color: "#aaa" }}>Tenant Slug (Immutable)</span>
              <input
                type="text"
                readOnly
                value="meridian-labs"
                className="mono"
                style={{ padding: "0.5rem 0.75rem", background: "#111", border: "1px solid #222", color: "#888" }}
              />
            </label>
          </div>
        </section>

        <section className="panel">
          <div className="panel-head">
            <div>
              <div className="eyebrow">GOVERNANCE ENFORCEMENT</div>
              <h2>Tone &amp; compliance gates</h2>
            </div>
          </div>
          <div style={{ padding: "1.25rem", display: "flex", flexDirection: "column", gap: "1rem" }}>
            <label style={{ display: "flex", flexDirection: "column", gap: "0.4rem", fontSize: "0.85rem" }}>
              <span style={{ color: "#aaa" }}>Minimum AI Tone &amp; Compliance Score to Submit (0–100)</span>
              <input
                type="number"
                min="0"
                max="100"
                value={defaultThreshold}
                onChange={(e) => setDefaultThreshold(e.target.value)}
                style={{ width: "120px", padding: "0.5rem 0.75rem", background: "#0a0a0a", border: "1px solid #333", color: "#fff" }}
              />
              <small style={{ color: "#777" }}>Submissions below this score require creator revision or manager sign-off.</small>
            </label>

            <label style={{ display: "flex", alignItems: "center", gap: "0.75rem", fontSize: "0.85rem", cursor: "pointer", marginTop: "0.5rem" }}>
              <input
                type="checkbox"
                checked={failClosed}
                onChange={(e) => setFailClosed(e.target.checked)}
                style={{ width: "16px", height: "16px", accentColor: "#C6FF00" }}
              />
              <div>
                <strong>Fail-Closed Verification</strong>
                <p style={{ margin: 0, color: "#888", fontSize: "0.75rem" }}>
                  Block approvals automatically if ungrounded claims or unresolved policy conflicts exist.
                </p>
              </div>
            </label>
          </div>
        </section>

        <div style={{ display: "flex", gap: "1rem", alignItems: "center" }}>
          <button type="submit" className="button lime-button">SAVE SETTINGS ↗</button>
          {saved && <span style={{ color: "#C6FF00", fontSize: "0.85rem" }}>✓ Settings updated successfully.</span>}
        </div>
      </form>
    </>
  );
}
