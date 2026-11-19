"use client";

import { useState } from "react";

export default function IntegrationsPage() {
  const [copied, setCopied] = useState<string | null>(null);

  const copyKey = (val: string) => {
    navigator.clipboard?.writeText(val);
    setCopied(val);
    setTimeout(() => setCopied(null), 2000);
  };

  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow blue">PLATFORM&nbsp; / &nbsp;07&nbsp; · &nbsp;INTEGRATIONS</div>
          <h1>Ecosystem &amp; API integrations</h1>
          <p>Connect ProofGate to your CMS, CI/CD publishing pipeline, and enterprise Identity Providers.</p>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
        <section className="panel">
          <div className="panel-head">
            <div>
              <div className="eyebrow">ENTERPRISE AUTH</div>
              <h2>OIDC &amp; Single Sign-On (SSO)</h2>
              <p>Configure OpenID Connect / SAML 2.0 federation for tenant isolation.</p>
            </div>
            <span className="role-pill">ACTIVE</span>
          </div>
          <div style={{ padding: "1.25rem", display: "flex", flexDirection: "column", gap: "0.75rem", fontSize: "0.85rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "#888" }}>Issuer URL:</span>
              <span className="mono">https://auth.meridianlabs.example</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "#888" }}>Algorithm:</span>
              <span className="mono">HS256 (OIDC/JWT Bearer)</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "#888" }}>Tenant Boundary:</span>
              <span className="mono">meridian-labs</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "#888" }}>Session Lifetime:</span>
              <span className="mono">24 Hours (Rolling)</span>
            </div>
          </div>
        </section>

        <section className="panel">
          <div className="panel-head">
            <div>
              <div className="eyebrow">DEVELOPER APIS</div>
              <h2>REST &amp; Webhook Access</h2>
              <p>Programmatic inspection API keys for automated CI/CD gating.</p>
            </div>
            <span className="role-pill">ENABLED</span>
          </div>
          <div style={{ padding: "1.25rem", display: "flex", flexDirection: "column", gap: "1rem" }}>
            <div>
              <small style={{ color: "#888", display: "block", marginBottom: "0.25rem" }}>PROD API ENDPOINT</small>
              <div style={{ display: "flex", gap: "0.5rem" }}>
                <input
                  readOnly
                  value="http://localhost:8000/api"
                  className="mono"
                  style={{ flex: 1, padding: "0.4rem 0.6rem", background: "#0a0a0a", border: "1px solid #333", color: "#fff", fontSize: "0.8rem" }}
                />
                <button
                  className="button dark-button"
                  style={{ padding: "0.4rem 0.8rem", fontSize: "0.75rem" }}
                  onClick={() => copyKey("http://localhost:8000/api")}
                >
                  {copied === "http://localhost:8000/api" ? "COPIED" : "COPY"}
                </button>
              </div>
            </div>
            <div>
              <small style={{ color: "#888", display: "block", marginBottom: "0.25rem" }}>WEBHOOK SUBSCRIBER</small>
              <span className="mono" style={{ fontSize: "0.8rem", color: "#C6FF00" }}>events: review.completed, policy.drift_detected</span>
            </div>
          </div>
        </section>

        <section className="panel">
          <div className="panel-head">
            <div>
              <div className="eyebrow">AI MODEL PROVIDER</div>
              <h2>Google Gemini 2.5 Flash / Pro</h2>
              <p>Contextual claim extraction, tone evaluation, and intent-preserving rewrites.</p>
            </div>
            <span className="role-pill">CONNECTED</span>
          </div>
          <div style={{ padding: "1.25rem", fontSize: "0.85rem", color: "#aaa" }}>
            <p>
              Integrated via the official <span className="mono" style={{ color: "#fff" }}>google-genai</span> SDK with strict fallback NLI heuristics if the API key is unconfigured.
            </p>
          </div>
        </section>

        <section className="panel">
          <div className="panel-head">
            <div>
              <div className="eyebrow">STORAGE &amp; DB</div>
              <h2>PostgreSQL &amp; SQLite</h2>
              <p>Persistent relational storage for immutable evidence records and audit events.</p>
            </div>
            <span className="role-pill">CONNECTED</span>
          </div>
          <div style={{ padding: "1.25rem", fontSize: "0.85rem", color: "#aaa" }}>
            <p>
              Supports persistent PostgreSQL via Docker Compose with zero-config fallback SQLite for lightweight local reviews.
            </p>
          </div>
        </section>
      </div>
    </>
  );
}
