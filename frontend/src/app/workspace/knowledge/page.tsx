"use client";

import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

type Fact = { id: string; fact_key: string; version: number; label: string; claim_text: string; owner: string; approval_status: string; source_name: string; source_version: string; effective_at: string };
type FactInput = { fact_key: string; label: string; claim_text: string; source_name: string; source_version: string; owner: string };
type Summary = { sources: number; facts: number; policies: number; expiring_soon: number };

const initial: FactInput = { fact_key: "", label: "", claim_text: "", source_name: "", source_version: "v1.0", owner: "Finance & Commercial Operations" };

export default function KnowledgePage() {
  const client = useQueryClient();
  const facts = useQuery({ queryKey: ["facts"], queryFn: () => api<Fact[]>("/api/knowledge/facts") });
  const summary = useQuery({ queryKey: ["knowledge-summary"], queryFn: () => api<Summary>("/api/knowledge/summary") });
  const [form, setForm] = useState(initial);
  const [message, setMessage] = useState("");
  const save = useMutation({ mutationFn: () => api<Fact>("/api/knowledge/facts", { method: "POST", body: JSON.stringify(form) }), onSuccess: async () => { setForm(initial); setMessage("Approved fact added to the organization ledger."); await client.invalidateQueries({ queryKey: ["facts"] }); await client.invalidateQueries({ queryKey: ["knowledge-summary"] }); } });
  function submit(event: FormEvent) { event.preventDefault(); setMessage(""); save.mutate(); }
  function update(key: keyof FactInput, value: string) { setForm((current) => ({ ...current, [key]: value })); }
  const byKey = facts.data?.reduce<Record<string, Fact[]>>((acc, fact) => { (acc[fact.fact_key] ??= []).push(fact); return acc; }, {}) ?? {};
  return <>
    <div className="page-heading"><div><div className="eyebrow blue">PLATFORM&nbsp; / &nbsp;02&nbsp; · &nbsp;SOURCE</div><h1>Brand intelligence</h1><p>Authoritative facts, versioned, accountable and ready for review.</p></div><a className="button dark-button" href="#add-fact">ADD APPROVED FACT ↗</a></div>
    <div className="metric-grid knowledge-metrics"><div className="metric-card"><small>ACTIVE KNOWLEDGE SOURCES</small><strong>{summary.data?.sources ?? 0}</strong><span>VERSIONED RECORDS</span></div><div className="metric-card lime"><small>APPROVED FACTS</small><strong>{summary.data?.facts ?? 0}</strong><span>TRACEABLE CLAIMS</span></div><div className="metric-card blue"><small>ENFORCED POLICIES</small><strong>{summary.data?.policies ?? 0}</strong><span>APPROVED VERSIONS</span></div><div className="metric-card dark"><small>EXPIRING SOON</small><strong>{String(summary.data?.expiring_soon ?? 0).padStart(2, "0")}</strong><span>NEXT 30 DAYS</span></div></div>
    <div className="knowledge-layout"><section className="panel knowledge-table"><div className="panel-head"><div><div className="eyebrow">SOURCE REGISTRY / {Object.keys(byKey).length} FACT GROUPS</div><h2>Version-controlled brand knowledge</h2></div></div><div className="table-header"><span>APPROVED FACT</span><span>VERSION</span><span>STATE</span></div>{facts.isLoading ? <div className="loading-state">Loading approved records…</div> : facts.error ? <div className="error-state">{(facts.error as Error).message}</div> : Object.entries(byKey).map(([key, versions]) => { const current = versions[0]; return <div className="fact-row" key={key}><div><strong>{current.label}</strong><small>{current.source_name} / {current.owner}</small></div><span className="mono">{current.source_version} · FACT V{current.version}</span><span className="status status-approved">APPROVED</span></div>; })}</section>
      <aside className="source-inspector"><div className="eyebrow lime">SOURCE OF TRUTH&nbsp; / &nbsp;LEDGER</div><h2>{facts.data?.[0]?.label ?? "No facts yet"}</h2><p className="inspector-category">{facts.data?.[0]?.source_name ?? "Add an approved source record"}</p><hr /><small>APPROVED ASSERTION</small><p className="assertion">{facts.data?.[0]?.claim_text ?? ""}</p><hr /><small>DOCUMENT / VERSION</small><p>{facts.data?.[0]?.source_name} / {facts.data?.[0]?.source_version}</p><small>ACCOUNTABLE OWNER</small><p>{facts.data?.[0]?.owner}</p><div className="verified-box">VERIFIED / VERSION PINNED<br /><br />Review findings cite the exact approved fact version used during analysis.</div></aside></div>
    <section className="panel add-fact-panel" id="add-fact"><div className="panel-head"><div><div className="eyebrow">KNOWLEDGE MANAGEMENT</div><h2>Register an approved fact</h2><p>Only a brand manager or administrator can add authoritative facts.</p></div><span className="role-pill">MANAGER ACCESS</span></div>
      <form className="form-grid" onSubmit={submit}><Field label="FACT KEY" value={form.fact_key} onChange={(v) => update("fact_key", v)} placeholder="e.g. fee" required /><Field label="CLAIM LABEL" value={form.label} onChange={(v) => update("label", v)} placeholder="Transfer fee" required /><Field label="APPROVED ASSERTION" value={form.claim_text} onChange={(v) => update("claim_text", v)} placeholder="The approved factual statement" required wide /><Field label="SOURCE DOCUMENT" value={form.source_name} onChange={(v) => update("source_name", v)} placeholder="Commercial Pricing Policy" required /><Field label="SOURCE VERSION" value={form.source_version} onChange={(v) => update("source_version", v)} placeholder="v1.0" required /><Field label="ACCOUNTABLE OWNER" value={form.owner} onChange={(v) => update("owner", v)} placeholder="Finance & Operations" required /><div className="form-actions"><span className="form-message">{save.error ? (save.error as Error).message : message}</span><button className="button lime-button" disabled={save.isPending}>{save.isPending ? "SAVING…" : "ADD APPROVED FACT ↗"}</button></div></form>
    </section>
  </>;
}

function Field({ label, value, onChange, placeholder, required, wide = false }: { label: string; value: string; onChange: (value: string) => void; placeholder: string; required?: boolean; wide?: boolean }) {
  return <label className={`field ${wide ? "wide" : ""}`}><span>{label}</span><input value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} required={required} /></label>;
}
