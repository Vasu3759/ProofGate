"use client";

import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Status } from "@/components/status";

type QueueItem = { id: string; title: string; channel: string; status: string; revision_number: number; content: string; creator: string; review: { findings: { id: string; status: string; severity: string; claim_text: string; explanation: string; evidence: { source_name: string; source_version: string; excerpt: string } | null }[] } | null };
type AuditItem = { id: string; action: string; actor: string; created_at: string; entity_id: string; metadata: Record<string, string> };
const roles: Record<string, string> = { "alex@meridianlabs.example": "creator", "dana@meridianlabs.example": "reviewer", "morgan@meridianlabs.example": "brand_manager" };

export default function ApprovalsPage() {
  const client = useQueryClient();
  const [email, setEmail] = useState("alex@meridianlabs.example");
  const [comments, setComments] = useState("");
  const [message, setMessage] = useState("");
  useEffect(() => {
    const sync = () => setEmail(localStorage.getItem("proofgate-demo-user") ?? "alex@meridianlabs.example");
    sync(); window.addEventListener("proofgate-user-change", sync);
    return () => window.removeEventListener("proofgate-user-change", sync);
  }, []);
  const queue = useQuery({ queryKey: ["approvals"], queryFn: () => api<QueueItem[]>("/api/approvals") });
  const audit = useQuery({ queryKey: ["audit"], queryFn: () => api<AuditItem[]>("/api/audit") });
  const decision = useMutation({ mutationFn: ({ id, value }: { id: string; value: string }) => api(`/api/submissions/${id}/decisions`, { method: "POST", body: JSON.stringify({ decision: value, comments }) }), onSuccess: async (_data, variables) => { setMessage(`Decision recorded for ${variables.id.slice(0, 8).toUpperCase()}.`); setComments(""); await client.invalidateQueries({ queryKey: ["approvals"] }); await client.invalidateQueries({ queryKey: ["audit"] }); await client.invalidateQueries({ queryKey: ["dashboard"] }); await client.invalidateQueries({ queryKey: ["submissions"] }); }, onError: (err) => setMessage((err as Error).message) });
  const canDecide = roles[email] === "reviewer" || roles[email] === "admin";
  return <>
    <div className="page-heading"><div><div className="eyebrow blue">PLATFORM&nbsp; / &nbsp;04&nbsp; · &nbsp;DECIDE</div><h1>Approval operations</h1><p>Human-led decisions, preserved context and a complete review trail.</p></div><span className="role-pill">{canDecide ? "REVIEWER ACCESS" : "READ ONLY · CREATOR"}</span></div>
    <div className="workflow-status"><div><small>WORKFLOW STATUS / HUMAN CONTROL</small><div><strong>{queue.data?.length ?? 0}</strong><span>WAITING</span><strong>{queue.data?.filter((item) => item.review?.findings.some((f) => f.severity === "critical"))?.length ?? 0}</strong><span>CRITICAL FINDINGS</span></div></div><span className="status status-in_review">GATED RELEASE</span></div>
    {message && <div className={message.startsWith("Decision") ? "success-state" : "error-state"}>{message}</div>}
    {queue.isLoading ? <div className="loading-state">Loading reviewer queue…</div> : queue.error ? <div className="error-state">{(queue.error as Error).message}</div> : queue.data?.length ? <div className="approval-layout"><section className="panel approval-queue"><div className="panel-head"><div><div className="eyebrow">01 / MANAGER QUEUE</div><h2>Review assignments</h2></div></div>{queue.data.map((item) => <article className="approval-card" key={item.id}><div className="approval-title"><div><h3>{item.title}</h3><p>{item.creator} / Revision v{item.revision_number} / {item.channel}</p></div><Status status={item.status} /></div><div className="approval-content">{item.content}</div><div className="approval-findings">{item.review?.findings.map((finding) => <div key={finding.id}><span className={`severity-dot ${finding.severity}`} /> <strong>{finding.claim_text}</strong><span>{finding.status}</span><p>{finding.evidence ? `${finding.evidence.source_name} ${finding.evidence.source_version}: ${finding.evidence.excerpt}` : finding.explanation}</p></div>)}</div>{canDecide ? <><label className="field"><span>REVIEWER COMMENT</span><textarea rows={2} value={comments} onChange={(event) => setComments(event.target.value)} placeholder="Add a decision note or requested change" /></label><div className="decision-actions"><button className="button outline-button" onClick={() => decision.mutate({ id: item.id, value: "needs_changes" })} disabled={decision.isPending}>REQUEST CHANGES</button><button className="button reject-button" onClick={() => decision.mutate({ id: item.id, value: "rejected" })} disabled={decision.isPending}>REJECT</button><button className="button lime-button" onClick={() => decision.mutate({ id: item.id, value: "approved" })} disabled={decision.isPending}>APPROVE ↗</button></div></> : <div className="notice-strip"><span>HUMAN DECISION REQUIRED</span><p>Switch to Dana Kim, the demo reviewer, to record a decision.</p></div>}</article>)}</section><aside className="audit-panel"><div className="audit-head"><div className="eyebrow">02 / AUDIT TRAIL</div><h2>Recorded events</h2></div><div className="audit-timeline">{audit.data?.map((event) => <div className="audit-event" key={event.id}><i /><small>{new Date(event.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</small><strong>{event.action.replaceAll(".", " ").replaceAll("_", " ")}</strong><span>{event.actor}</span><span>REV {String(event.metadata.revision_number ?? event.metadata.revision_id?.slice(0, 8) ?? "—").toUpperCase()}</span></div>)}</div>{!audit.data?.length && <p className="audit-empty">No audit events have been recorded yet.</p>}<div className="signature-card"><small>APPEND-ONLY WORKFLOW EVENT</small><code>ORGANIZATION SCOPED / REVISION PINNED</code></div></aside></div> : <section className="panel empty-approval"><div className="eyebrow">MANAGER QUEUE</div><h2>No submissions are awaiting approval.</h2><p>Create and review a submission in Review Studio, then route its current revision here for a human decision.</p><a className="button dark-button" href="/workspace/review">OPEN REVIEW STUDIO ↗</a></section>}
  </>;
}
