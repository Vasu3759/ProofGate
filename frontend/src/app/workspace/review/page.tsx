"use client";

import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Status } from "@/components/status";

type Finding = { id: string; severity: string; claim_text: string; status: string; explanation: string; evidence: { fact_key: string; label: string; source_name: string; source_version: string; excerpt: string } | null; suggestion: { text: string; rationale: string } | null };
type Review = { id: string; revision_id: string; created_at: string; policies: { version: number; rule_text: string }[]; findings: Finding[] };
type Submission = { id: string; title: string; status: string; revision_id: string; revision_number: number };
const sample = "MeridianPay offers completely free international transfers, available instantly in over 150 countries.";

export default function ReviewPage() {
  const client = useQueryClient();
  const profile = useQuery({ queryKey: ["me"], queryFn: () => api<{ name: string }>("/api/me") });
  const history = useQuery({ queryKey: ["submissions"], queryFn: () => api<{ id: string; title: string; status: string; revision: number }[]>("/api/submissions") });
  const [title, setTitle] = useState("International launch / LinkedIn");
  const [channel, setChannel] = useState("LinkedIn / Public marketing");
  const [content, setContent] = useState(sample);
  const [active, setActive] = useState<Submission | null>(null);
  const [review, setReview] = useState<Review | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const createAndReview = useMutation({ mutationFn: async () => {
    const submission = await api<Submission>("/api/submissions", { method: "POST", body: JSON.stringify({ title, channel, content }) });
    const result = await api<Review>(`/api/submissions/${submission.id}/review`, { method: "POST" });
    return { submission, result };
  }, onSuccess: async ({ submission, result }) => { setActive(submission); setReview(result); setNotice(""); await client.invalidateQueries({ queryKey: ["submissions"] }); await client.invalidateQueries({ queryKey: ["dashboard"] }); }, onError: (err) => setError((err as Error).message) });
  const rerun = useMutation({ mutationFn: async (newContent: string) => {
    if (!active) throw new Error("Create a submission first.");
    await api(`/api/submissions/${active.id}/revisions`, { method: "POST", body: JSON.stringify({ content: newContent }) });
    const result = await api<Review>(`/api/submissions/${active.id}/review`, { method: "POST" });
    return result;
  }, onSuccess: async (result) => { setReview(result); setActive((current) => current ? ({ ...current, revision_id: result.revision_id, revision_number: current.revision_number + 1, status: result.findings.some((finding) => finding.status === "contradicted" || finding.status === "policy_violation") ? "needs_changes" : "reviewed" }) : current); setNotice("New revision saved and checked against approved knowledge."); await client.invalidateQueries({ queryKey: ["submissions"] }); }, onError: (err) => setError((err as Error).message) });
  const submitForReview = useMutation({ mutationFn: () => api(`/api/submissions/${active?.id}/submit`, { method: "POST" }), onSuccess: async () => { setActive((current) => current ? ({ ...current, status: "in_review" }) : current); setNotice("Submitted to the human approval queue."); await client.invalidateQueries({ queryKey: ["submissions"] }); await client.invalidateQueries({ queryKey: ["dashboard"] }); }, onError: (err) => setError((err as Error).message) });
  function submit(event: FormEvent) { event.preventDefault(); setError(""); setNotice(""); createAndReview.mutate(); }
  function applyCorrections() {
    if (!review) return;
    let corrected = content;
    for (const finding of review.findings) {
      if (!finding.suggestion || finding.suggestion.text.startsWith("Remove this")) continue;
      corrected = corrected.replace(finding.claim_text, finding.suggestion.text);
    }
    setContent(corrected);
    rerun.mutate(corrected);
  }
  const issueCount = review?.findings.filter((finding) => finding.status !== "supported").length ?? 0;
  const locked = active ? ["in_review", "approved", "rejected"].includes(active.status) : false;
  return <>
    <div className="page-heading"><div><div className="eyebrow blue">PLATFORM&nbsp; / &nbsp;03&nbsp; · &nbsp;INSPECT</div><h1>Content review</h1><p>Every claim verified. Every issue explained. No silent rewrites.</p></div><button className="button lime-button" onClick={() => active ? rerun.mutate(content) : document.querySelector<HTMLFormElement>(".review-form")?.requestSubmit()} disabled={locked || createAndReview.isPending || rerun.isPending}>RUN COMPLIANCE ↗</button></div>
    <div className={`review-workstation ${locked ? "locked" : ""}`}>
      <section className="editor-pane"><div className="pane-band"><span>01 / CONTENT INPUT</span><span>{active ? `REVISION / ${review ? "REVIEWED" : "DRAFT"}` : "NEW SUBMISSION"}&nbsp; · &nbsp;TEXT / SOCIAL</span></div><form className="review-form" onSubmit={submit}><label className="field"><span>CONTENT TITLE</span><input value={title} onChange={(event) => setTitle(event.target.value)} required disabled={locked} /></label><div className="content-meta"><span>AUTHOR: {profile.data?.name ?? "DEMO USER"}</span><span>{content.trim().split(/\s+/).filter(Boolean).length} WORDS</span></div><label className="field"><span>PUBLISHING CHANNEL</span><input value={channel} onChange={(event) => setChannel(event.target.value)} required disabled={locked} /></label><div className="editor-card"><div className="eyebrow blue">MERIDIAN LABS&nbsp; / &nbsp;CAMPAIGN MATERIAL</div><textarea id="content-editor" value={content} onChange={(event) => setContent(event.target.value)} rows={8} aria-label="Content to review" disabled={locked} /><div className="editor-hint">{locked ? "This revision is submitted or decided and is preserved as read-only." : "Paste or edit text here. Demo facts are synthetic and belong to Meridian Labs."}</div></div>{!active && <button className="button dark-button full-button" disabled={createAndReview.isPending}>{createAndReview.isPending ? "ANALYZING…" : "CREATE SUBMISSION & RUN REVIEW ↗"}</button>}</form>{active && <><div className="revision-footer"><span>CONTENT REVISION HASH</span><code>{review?.revision_id.slice(0, 8).toUpperCase() ?? active.revision_id.slice(0, 8).toUpperCase()}</code></div>{!locked && <div className="review-actions"><button className="button outline-button" onClick={() => { setActive(null); setReview(null); setError(""); }}>NEW SUBMISSION</button><button className="button lime-button" onClick={applyCorrections} disabled={!review || rerun.isPending}>{rerun.isPending ? "SAVING + CHECKING…" : "APPLY SUGGESTIONS & RECHECK ↗"}</button></div>}{review && !locked && <button className="button dark-button full-button submit-review" onClick={() => submitForReview.mutate()} disabled={submitForReview.isPending}>{submitForReview.isPending ? "SUBMITTING…" : "SUBMIT REVISION FOR HUMAN REVIEW ↗"}</button>}</>}
        {error && <div className="error-state">{error}</div>}{notice && <div className="success-state">{notice}</div>}
      </section>
      <aside className="inspector-pane"><div className="pane-band lime-band"><span>02 / VALIDATION &amp; EVIDENCE</span><span>DETERMINISTIC / V1</span></div>{!review ? <div className="inspector-empty"><div className="mono">READY WHEN YOU ARE</div><h2>Evidence before approval.</h2><p>Run a review to inspect claims against the approved Meridian Labs source ledger.</p><div className="demo-claim"><small>DEMO CLAIM</small><p>“Free, instant transfers to 150+ countries.”</p></div></div> : <><div className="review-summary"><span className="mono">CHECK COMPLETE&nbsp; / &nbsp;{issueCount.toString().padStart(2, "0")} ISSUES DETECTED</span><strong>{review.findings.length.toString().padStart(2, "0")}</strong><span>FINDINGS</span></div><div className="finding-list">{review.findings.length === 0 ? <div className="success-state">No issues detected. The review run is still pinned to the exact content revision and policy version.</div> : review.findings.map((finding, index) => <article className={`finding-card ${finding.status}`} key={finding.id}><div className="finding-kicker">{String(index + 1).padStart(2, "0")}&nbsp; · &nbsp;{finding.severity.toUpperCase()} / {finding.status.toUpperCase()}</div><h3>{finding.status === "contradicted" ? "Approved evidence contradicts this claim." : finding.status === "unverified" ? "This claim lacks approved proof." : "Policy issue detected."}</h3><blockquote>“{finding.claim_text}”</blockquote><p>{finding.explanation}</p>{finding.evidence ? <div className="citation"><span>SOURCE: {finding.evidence.source_name} / {finding.evidence.source_version} / {finding.evidence.fact_key.toUpperCase()}</span><p>{finding.evidence.excerpt}</p></div> : <div className="no-citation">NO AUTHORITATIVE SOURCE FOUND</div>}{finding.suggestion && <div className="suggestion"><small>SUGGESTED LANGUAGE</small><p>{finding.suggestion.text}</p></div>}</article>)}</div><div className="policy-pin"><span>POLICY VERSION PINNED</span><p>{review.policies.map((policy) => `V${policy.version}`).join(" · ") || "No active policy versions"}</p></div></>}</aside>
    </div>
    <section className="panel review-history"><div className="panel-head"><div><div className="eyebrow">SUBMISSION HISTORY</div><h2>Recent content reviews</h2></div><span className="role-pill">{history.data?.length ?? 0} RECORDS</span></div>{history.data?.length ? <div className="history-list">{history.data.map((item) => <button key={item.id} className="history-row" onClick={async () => { setError(""); try { const detail = await api<{ id: string; title: string; channel: string; status: string; revisions: { id: string; number: number; content: string }[]; review_runs: Review[] }>(`/api/submissions/${item.id}`); const revision = detail.revisions[0]; setTitle(detail.title); setChannel(detail.channel); setContent(revision.content); setActive({ id: detail.id, title: detail.title, status: detail.status, revision_id: revision.id, revision_number: revision.number }); setReview(detail.review_runs[0] ?? null); } catch (err) { setError((err as Error).message); } }}><span>{item.title}</span><span>REV {item.revision}</span><Status status={item.status} /></button>)}</div> : <p className="muted-copy">Submissions created in this workspace appear here.</p>}</section>
  </>;
}
