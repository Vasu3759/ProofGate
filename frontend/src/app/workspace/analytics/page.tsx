"use client";

import Link from "next/link";

export default function AnalyticsPage() {
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow blue">PLATFORM&nbsp; / &nbsp;06&nbsp; · &nbsp;ANALYTICS</div>
          <h1>Governance analytics</h1>
          <p>Real-time brand compliance metrics, approval velocity, and policy violation distributions.</p>
        </div>
        <Link className="button lime-button" href="/workspace/review">RUN REVIEW ↗</Link>
      </div>

      <div className="metric-grid">
        <div className="metric-card">
          <small>AVG VERIFICATION SCORE</small>
          <strong style={{ color: "#C6FF00" }}>92.4%</strong>
          <span>+4.1% THIS MONTH</span>
        </div>
        <div className="metric-card lime">
          <small>FIRST-PASS APPROVAL RATE</small>
          <strong>78.6%</strong>
          <span>ACROSS CHANNELS</span>
        </div>
        <div className="metric-card orange">
          <small>COMMON CONTRADICTION</small>
          <strong>FEE / PRICING</strong>
          <span>38% OF FINDINGS</span>
        </div>
        <div className="metric-card blue">
          <small>MEDIAN HUMAN REVIEW</small>
          <strong>14m</strong>
          <span>TURNAROUND TIME</span>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem", marginTop: "1.5rem" }}>
        <section className="panel">
          <div className="panel-head">
            <div>
              <div className="eyebrow">DISTRIBUTION</div>
              <h2>Findings by category</h2>
            </div>
          </div>
          <div style={{ padding: "1.25rem", display: "flex", flexDirection: "column", gap: "1rem" }}>
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.4rem", fontSize: "0.85rem" }}>
                <span>Fee &amp; Commercial Pricing Discrepancies</span>
                <strong>38%</strong>
              </div>
              <div style={{ height: "6px", background: "#222" }}>
                <div style={{ width: "38%", height: "100%", background: "#FF5252" }} />
              </div>
            </div>
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.4rem", fontSize: "0.85rem" }}>
                <span>Unsupported Guarantees &amp; Superlatives</span>
                <strong>31%</strong>
              </div>
              <div style={{ height: "6px", background: "#222" }}>
                <div style={{ width: "31%", height: "100%", background: "#FFB300" }} />
              </div>
            </div>
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.4rem", fontSize: "0.85rem" }}>
                <span>Settlement &amp; SLA Timeframe Deviations</span>
                <strong>19%</strong>
              </div>
              <div style={{ height: "6px", background: "#222" }}>
                <div style={{ width: "19%", height: "100%", background: "#40C4FF" }} />
              </div>
            </div>
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.4rem", fontSize: "0.85rem" }}>
                <span>Market Availability Count Discrepancies</span>
                <strong>12%</strong>
              </div>
              <div style={{ height: "6px", background: "#222" }}>
                <div style={{ width: "12%", height: "100%", background: "#C6FF00" }} />
              </div>
            </div>
          </div>
        </section>

        <section className="panel">
          <div className="panel-head">
            <div>
              <div className="eyebrow">CHANNELS</div>
              <h2>Volume by marketing channel</h2>
            </div>
          </div>
          <div style={{ padding: "1.25rem", display: "flex", flexDirection: "column", gap: "1rem" }}>
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.4rem", fontSize: "0.85rem" }}>
                <span>Social Media &amp; Digital Paid Ads</span>
                <strong>45% (18 assets)</strong>
              </div>
              <div style={{ height: "6px", background: "#222" }}>
                <div style={{ width: "45%", height: "100%", background: "#C6FF00" }} />
              </div>
            </div>
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.4rem", fontSize: "0.85rem" }}>
                <span>Product Marketing Briefs</span>
                <strong>30% (12 assets)</strong>
              </div>
              <div style={{ height: "6px", background: "#222" }}>
                <div style={{ width: "30%", height: "100%", background: "#40C4FF" }} />
              </div>
            </div>
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.4rem", fontSize: "0.85rem" }}>
                <span>Email &amp; Lifecycle Campaigns</span>
                <strong>25% (10 assets)</strong>
              </div>
              <div style={{ height: "6px", background: "#222" }}>
                <div style={{ width: "25%", height: "100%", background: "#FFB300" }} />
              </div>
            </div>
          </div>
        </section>
      </div>
    </>
  );
}
