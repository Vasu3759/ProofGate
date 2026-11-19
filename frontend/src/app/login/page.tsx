"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { API_URL } from "@/lib/api";

const PRESET_ACCOUNTS = [
  { email: "alex@meridianlabs.example", name: "Alex Rivera", role: "Creator", desc: "Author marketing copy, upload documents, run compliance checks." },
  { email: "dana@meridianlabs.example", name: "Dana Kim", role: "Reviewer", desc: "Inspect flagged evidence, evaluate revisions, record approvals." },
  { email: "morgan@meridianlabs.example", name: "Morgan Lee", role: "Brand Manager", desc: "Register authoritative facts, resolve policy conflicts, manage lineage." },
];

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("alex@meridianlabs.example");
  const [organization, setOrganization] = useState("meridian-labs");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleLogin = async (selectedEmail?: string) => {
    const targetEmail = selectedEmail || email;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/api/auth/token`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: targetEmail,
          organization_slug: organization,
        }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({ detail: "Login failed" }));
        throw new Error(data.detail || "Authentication failed");
      }

      const data = await res.json();
      localStorage.setItem("proofgate-jwt-token", data.access_token);
      localStorage.setItem("proofgate-demo-user", data.user.email);
      window.dispatchEvent(new Event("proofgate-user-change"));
      router.push("/workspace");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to connect to authentication server.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: "100vh", background: "#0a0a0a", color: "#ededed", display: "flex", flexDirection: "column" }}>
      <header style={{ padding: "1.5rem 2.5rem", borderBottom: "1px solid #222", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <Link className="brand-lockup light" href="/" style={{ textDecoration: "none" }}>
          <span className="brand-mark"><i /><i /></span>
          <b style={{ letterSpacing: "0.1em" }}>PROOFGATE</b>
        </Link>
        <span style={{ fontSize: "0.75rem", color: "#888", letterSpacing: "0.15em" }}>ENTERPRISE AUTH GATEWAY</span>
      </header>

      <main style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", padding: "2rem" }}>
        <div style={{ width: "100%", maxWidth: "560px", background: "#111", border: "1px solid #282828", padding: "2.5rem" }}>
          <div style={{ marginBottom: "2rem" }}>
            <span style={{ color: "#C6FF00", fontSize: "0.75rem", letterSpacing: "0.2em", fontWeight: 700 }}>OIDC / JWT AUTHENTICATION</span>
            <h1 style={{ fontSize: "1.75rem", margin: "0.5rem 0", fontWeight: 700 }}>Sign in to ProofGate</h1>
            <p style={{ color: "#888", fontSize: "0.875rem", margin: 0 }}>
              Authenticate into your enterprise tenant workspace with verifiable RBAC identity.
            </p>
          </div>

          {error && (
            <div style={{ background: "rgba(255, 82, 82, 0.1)", border: "1px solid #FF5252", padding: "0.75rem 1rem", color: "#FF5252", fontSize: "0.85rem", marginBottom: "1.5rem" }}>
              {error}
            </div>
          )}

          <div style={{ marginBottom: "2rem" }}>
            <span style={{ display: "block", fontSize: "0.75rem", color: "#888", letterSpacing: "0.1em", marginBottom: "0.75rem" }}>
              SELECT VERIFIED TENANT IDENTITY:
            </span>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
              {PRESET_ACCOUNTS.map((acc) => (
                <button
                  key={acc.email}
                  type="button"
                  onClick={() => {
                    setEmail(acc.email);
                    handleLogin(acc.email);
                  }}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "0.85rem 1rem",
                    background: email === acc.email ? "#1a1a1a" : "#141414",
                    border: `1px solid ${email === acc.email ? "#C6FF00" : "#282828"}`,
                    color: "#fff",
                    textAlign: "left",
                    cursor: "pointer",
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 600, fontSize: "0.9rem" }}>{acc.name}</div>
                    <div style={{ color: "#777", fontSize: "0.75rem" }}>{acc.email}</div>
                  </div>
                  <span
                    style={{
                      background: acc.role === "Brand Manager" ? "#FFB300" : acc.role === "Reviewer" ? "#40C4FF" : "#C6FF00",
                      color: "#000",
                      padding: "2px 8px",
                      fontSize: "0.7rem",
                      fontWeight: 700,
                      letterSpacing: "0.05em",
                    }}
                  >
                    {acc.role.toUpperCase()}
                  </span>
                </button>
              ))}
            </div>
          </div>

          <div style={{ borderTop: "1px solid #222", paddingTop: "1.5rem" }}>
            <label style={{ display: "block", fontSize: "0.75rem", color: "#888", marginBottom: "0.4rem" }}>
              CUSTOM EMAIL IDENTITY
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="user@organization.example"
              style={{ width: "100%", padding: "0.6rem 0.8rem", background: "#0a0a0a", border: "1px solid #333", color: "#fff", marginBottom: "1rem", fontSize: "0.85rem" }}
            />

            <label style={{ display: "block", fontSize: "0.75rem", color: "#888", marginBottom: "0.4rem" }}>
              TENANT SLUG
            </label>
            <input
              type="text"
              value={organization}
              onChange={(e) => setOrganization(e.target.value)}
              style={{ width: "100%", padding: "0.6rem 0.8rem", background: "#0a0a0a", border: "1px solid #333", color: "#fff", marginBottom: "1.5rem", fontSize: "0.85rem" }}
            />

            <button
              onClick={() => handleLogin()}
              disabled={loading}
              className="button lime-button"
              style={{ width: "100%", padding: "0.75rem", justifyContent: "center", cursor: loading ? "not-allowed" : "pointer" }}
            >
              {loading ? "AUTHENTICATING & ISSUING TOKEN…" : "SIGN IN & ENTER WORKSPACE ↗"}
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
