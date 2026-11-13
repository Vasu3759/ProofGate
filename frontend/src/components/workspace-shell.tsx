"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

const users = [
  { email: "alex@meridianlabs.example", name: "Alex Rivera", role: "Creator" },
  { email: "dana@meridianlabs.example", name: "Dana Kim", role: "Reviewer" },
  { email: "morgan@meridianlabs.example", name: "Morgan Lee", role: "Brand manager" },
];
const nav = [
  { href: "/workspace", number: "01", label: "Overview" },
  { href: "/workspace/knowledge", number: "02", label: "Brand knowledge" },
  { href: "/workspace/review", number: "03", label: "Review studio" },
  { href: "/workspace/approvals", number: "04", label: "Approvals" },
];

export function WorkspaceShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const queryClient = useQueryClient();
  const [email, setEmail] = useState(users[0].email);
  useEffect(() => {
    const saved = localStorage.getItem("proofgate-demo-user");
    if (saved && users.some((user) => user.email === saved)) setEmail(saved);
  }, []);
  const current = users.find((user) => user.email === email) ?? users[0];
  function switchUser(value: string) {
    setEmail(value);
    localStorage.setItem("proofgate-demo-user", value);
    queryClient.clear();
    window.dispatchEvent(new Event("proofgate-user-change"));
  }
  return <div className="app-shell">
    <aside className="sidebar">
      <Link className="brand-lockup" href="/workspace"><span className="brand-mark"><i /><i /></span><b>PROOFGATE</b></Link>
      <div className="sidebar-caption">POLICY / EVIDENCE / CONTROL</div>
      <div className="sidebar-rule" />
      <div className="sidebar-label">01&nbsp; WORKSPACE</div>
      <nav className="side-nav" aria-label="Workspace">
        {nav.map((item) => <Link key={item.href} href={item.href} className={`nav-item ${pathname === item.href ? "active" : ""}`}><span>{item.number}</span>{item.label}</Link>)}
        <div className="nav-item muted" aria-disabled="true"><span>05</span>Impact radar <em>PLANNED</em></div>
      </nav>
      <div className="sidebar-label platform-label">02&nbsp; PLATFORM</div>
      <div className="platform-links"><span>06&nbsp; Analytics</span><span>07&nbsp; Integrations</span><span>08&nbsp; Settings</span></div>
      <div className="workspace-health"><small>WORKSPACE HEALTH</small><strong>DEMO WORKSPACE</strong><span>LOCAL SYNTHETIC DATA</span></div>
      <div className="sidebar-user"><span className="avatar">{current.name.split(" ").map((part) => part[0]).join("")}</span><div><strong>{current.name}</strong><small>{current.role.toUpperCase()}</small></div></div>
    </aside>
    <main className="workspace-main">
      <div className="utility-bar"><span>PROOFGATE&nbsp;&nbsp; / &nbsp;&nbsp;MERIDIAN LABS&nbsp;&nbsp; / &nbsp;&nbsp;WORKSPACE</span><div><span className="confidential">CONFIDENTIAL&nbsp; • &nbsp;DEMO ENVIRONMENT</span><label className="user-switch"><span>ACT AS</span><select aria-label="Demo user" value={email} onChange={(event) => switchUser(event.target.value)}>{users.map((user) => <option key={user.email} value={user.email}>{user.name} · {user.role}</option>)}</select></label></div></div>
      <div className="workspace-content">{children}</div>
    </main>
  </div>;
}
