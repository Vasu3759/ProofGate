"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Status } from "@/components/status";

type Dashboard = { reviews_completed: number; submissions: number; pending_approvals: number; needs_changes: number; decisions: number; recent: { id: string; title: string; status: string }[] };

export default function ControlCenter() {
  const query = useQuery({ queryKey: ["dashboard"], queryFn: () => api<Dashboard>("/api/dashboard") });
  const data = query.data;
  return <>
    <div className="page-heading"><div><div className="eyebrow blue">PLATFORM&nbsp; / &nbsp;01&nbsp; · &nbsp;OVERVIEW</div><h1>Control center</h1><p>Review activity and governance status for Meridian Labs.</p></div><Link className="button lime-button" href="/workspace/review">START A REVIEW ↗</Link></div>
    {query.isLoading ? <div className="loading-state">Loading workspace metrics…</div> : query.error ? <div className="error-state">{(query.error as Error).message}</div> : <>
      <div className="metric-grid"><Metric label="REVIEWS COMPLETED" value={data?.reviews_completed ?? 0} note="COMPLETED RUNS" /><Metric label="PENDING APPROVALS" value={data?.pending_approvals ?? 0} note="AWAITING HUMAN REVIEW" accent="lime" /><Metric label="NEEDS CHANGES" value={data?.needs_changes ?? 0} note="CREATOR ACTION" accent="orange" /><Metric label="DECISIONS RECORDED" value={data?.decisions ?? 0} note="AUDIT EVENTS" accent="blue" /></div>
      <section className="panel recent-panel"><div className="panel-head"><div><div className="eyebrow">WORKSPACE ACTIVITY</div><h2>Recent submissions</h2></div><Link href="/workspace/approvals" className="text-link">OPEN APPROVAL QUEUE ↗</Link></div>{data?.recent.length ? <div className="activity-list">{data.recent.map((row) => <Link key={row.id} href="/workspace/review" className="activity-row"><span className="activity-dot" /><strong>{row.title}</strong><Status status={row.status} /><small>{row.id.slice(0, 8).toUpperCase()}</small></Link>)}</div> : <div className="empty-state"><strong>No reviews yet.</strong><span>Start with the synthetic Meridian Labs scenario to create the first audit trail.</span><Link className="button dark-button" href="/workspace/review">CREATE FIRST REVIEW ↗</Link></div>}</section>
      <div className="notice-strip"><span>DEMO ENVIRONMENT</span><p>Metrics reflect this local workspace and its synthetic records. They are not production performance claims.</p></div>
    </>}
  </>;
}

function Metric({ label, value, note, accent = "" }: { label: string; value: number; note: string; accent?: string }) {
  return <div className={`metric-card ${accent}`}><small>{label}</small><strong>{value}</strong><span>{note}</span></div>;
}
