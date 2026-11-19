"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

type Conflict = {
  id: string;
  conflict_type: string;
  description: string;
  status: string;
  policy_a: { id: string; version: number; scope: string; precedence: number; rule_text: string } | null;
  policy_b: { id: string; version: number; scope: string; precedence: number; rule_text: string } | null;
  created_at: string;
};

type ReReviewTaskItem = {
  id: string;
  submission_id: string;
  title: string;
  channel: string;
  trigger_type: string;
  impact_summary: string;
  status: string;
  created_at: string;
};

type ImpactGraphData = {
  nodes: { id: string; type: string; label: string; status?: string }[];
  edges: { source: string; target: string; relationship: string }[];
};

export default function ImpactRadarPage() {
  const queryClient = useQueryClient();
  const [resolvingConflictId, setResolvingConflictId] = useState<string | null>(null);
  const [resolutionNotes, setResolutionNotes] = useState("");
  const [newPrecedence, setNewPrecedence] = useState<number>(10);

  const conflicts = useQuery({
    queryKey: ["policy-conflicts"],
    queryFn: () => api<Conflict[]>("/api/policies/conflicts"),
  });

  const tasks = useQuery({
    queryKey: ["impact-tasks"],
    queryFn: () => api<ReReviewTaskItem[]>("/api/impact/tasks"),
  });

  const graph = useQuery({
    queryKey: ["impact-graph"],
    queryFn: () => api<ImpactGraphData>("/api/impact/graph"),
  });

  const resolveConflict = useMutation({
    mutationFn: async ({ conflictId, winnerId }: { conflictId: string; winnerId?: string }) => {
      return api(`/api/policies/conflicts/${conflictId}/resolve`, {
        method: "POST",
        body: JSON.stringify({
          resolution_notes: resolutionNotes || "Precedence established and ambiguity resolved by brand manager.",
          winner_version_id: winnerId,
          new_precedence: newPrecedence,
        }),
      });
    },
    onSuccess: async () => {
      setResolvingConflictId(null);
      setResolutionNotes("");
      await queryClient.invalidateQueries({ queryKey: ["policy-conflicts"] });
    },
  });

  const resolveTask = useMutation({
    mutationFn: async (taskId: string) => {
      return api(`/api/impact/tasks/${taskId}/resolve`, { method: "POST" });
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["impact-tasks"] });
    },
  });

  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow blue">PLATFORM&nbsp; / &nbsp;05&nbsp; · &nbsp;INTELLIGENCE</div>
          <h1>Impact radar &amp; policy intelligence</h1>
          <p>
            Detect conflicting policy directives, map change-impact graphs, and execute
            targeted re-reviews before publishing.
          </p>
        </div>
      </div>

      {/* METRIC CARDS */}
      <div className="metric-grid knowledge-metrics" style={{ marginBottom: "1.5rem" }}>
        <div className="metric-card">
          <small>UNRESOLVED CONFLICTS</small>
          <strong style={{ color: conflicts.data?.length ? "#FFB300" : "#C6FF00" }}>
            {String(conflicts.data?.length ?? 0).padStart(2, "0")}
          </strong>
          <span>POLICY DIRECTIVES</span>
        </div>
        <div className="metric-card lime">
          <small>TARGETED RE-REVIEWS</small>
          <strong style={{ color: tasks.data?.length ? "#FF5252" : "#C6FF00" }}>
            {String(tasks.data?.length ?? 0).padStart(2, "0")}
          </strong>
          <span>IMPACTED ASSETS</span>
        </div>
        <div className="metric-card blue">
          <small>CHANGE-IMPACT NODES</small>
          <strong>{graph.data?.nodes?.length ?? 0}</strong>
          <span>LINEAGE GRAPH</span>
        </div>
        <div className="metric-card dark">
          <small>LINEAGE EDGES</small>
          <strong>{graph.data?.edges?.length ?? 0}</strong>
          <span>DEPENDENCY LINKS</span>
        </div>
      </div>

      {/* SECTION 1: POLICY CONFLICT INTELLIGENCE */}
      <section className="panel" style={{ marginBottom: "1.5rem" }}>
        <div className="panel-head">
          <div>
            <div className="eyebrow">POLICY INTELLIGENCE</div>
            <h2>Active policy conflicts &amp; precedence ambiguity</h2>
            <p>
              When brand rules contradict each other or have identical precedence, managers
              must record explicit priority resolutions.
            </p>
          </div>
          <span className="role-pill">MANAGER GOVERNANCE</span>
        </div>

        {conflicts.isLoading ? (
          <div className="loading-state">Analyzing brand policy precedence…</div>
        ) : !conflicts.data || conflicts.data.length === 0 ? (
          <div className="success-state" style={{ margin: "1rem" }}>
            No policy conflicts detected. All active brand policies have clear precedence and harmonious scope definitions.
          </div>
        ) : (
          <div style={{ padding: "1rem", display: "flex", flexDirection: "column", gap: "1rem" }}>
            {conflicts.data.map((conflict) => (
              <div
                key={conflict.id}
                style={{
                  background: "rgba(255, 179, 0, 0.05)",
                  border: "1px solid rgba(255, 179, 0, 0.3)",
                  padding: "1rem",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div>
                    <span
                      style={{
                        background: "#FFB300",
                        color: "#000",
                        padding: "2px 6px",
                        fontSize: "0.7rem",
                        fontWeight: 700,
                        letterSpacing: "0.08em",
                      }}
                    >
                      {conflict.conflict_type.toUpperCase()}
                    </span>
                    <p style={{ marginTop: "0.5rem", fontSize: "0.88rem", fontWeight: 500 }}>
                      {conflict.description}
                    </p>
                  </div>
                  <button
                    className="button outline-button"
                    style={{ fontSize: "0.75rem", padding: "0.4rem 0.8rem" }}
                    onClick={() => setResolvingConflictId(conflict.id)}
                  >
                    RESOLVE CONFLICT ↗
                  </button>
                </div>

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr",
                    gap: "1rem",
                    marginTop: "0.85rem",
                    fontSize: "0.8rem",
                    borderTop: "1px solid rgba(255, 255, 255, 0.08)",
                    paddingTop: "0.75rem",
                  }}
                >
                  <div>
                    <span style={{ color: "#888", display: "block" }}>POLICY A (Precedence: {conflict.policy_a?.precedence})</span>
                    <div style={{ color: "#eee", marginTop: "2px" }}>{conflict.policy_a?.rule_text}</div>
                  </div>
                  <div>
                    <span style={{ color: "#888", display: "block" }}>POLICY B (Precedence: {conflict.policy_b?.precedence})</span>
                    <div style={{ color: "#eee", marginTop: "2px" }}>{conflict.policy_b?.rule_text}</div>
                  </div>
                </div>

                {resolvingConflictId === conflict.id && (
                  <div
                    style={{
                      marginTop: "1rem",
                      background: "rgba(0, 0, 0, 0.4)",
                      padding: "1rem",
                      border: "1px solid rgba(255, 255, 255, 0.15)",
                    }}
                  >
                    <div style={{ fontSize: "0.8rem", fontWeight: 700, marginBottom: "0.5rem" }}>
                      RECORD PRECEDENCE RESOLUTION
                    </div>
                    <textarea
                      placeholder="Explain the legal or brand rationale for establishing precedence..."
                      value={resolutionNotes}
                      onChange={(e) => setResolutionNotes(e.target.value)}
                      rows={2}
                      style={{ width: "100%", padding: "0.5rem", marginBottom: "0.5rem", background: "#111", color: "#fff", border: "1px solid #333" }}
                    />
                    <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                      <button
                        className="button lime-button"
                        style={{ fontSize: "0.75rem", padding: "0.4rem 0.8rem" }}
                        disabled={resolveConflict.isPending}
                        onClick={() => resolveConflict.mutate({ conflictId: conflict.id, winnerId: conflict.policy_a?.id })}
                      >
                        PRIORITIZE POLICY A (TIER 10)
                      </button>
                      <button
                        className="button outline-button"
                        style={{ fontSize: "0.75rem", padding: "0.4rem 0.8rem" }}
                        disabled={resolveConflict.isPending}
                        onClick={() => resolveConflict.mutate({ conflictId: conflict.id, winnerId: conflict.policy_b?.id })}
                      >
                        PRIORITIZE POLICY B (TIER 10)
                      </button>
                      <button
                        className="button dark-button"
                        style={{ fontSize: "0.75rem", padding: "0.4rem 0.8rem" }}
                        onClick={() => setResolvingConflictId(null)}
                      >
                        CANCEL
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      {/* SECTION 2: TARGETED RE-REVIEW WORK QUEUE */}
      <section className="panel" style={{ marginBottom: "1.5rem" }}>
        <div className="panel-head">
          <div>
            <div className="eyebrow">CHANGE-IMPACT QUEUE</div>
            <h2>Targeted re-review work items</h2>
            <p>
              When a source fact or policy changes, only impacted content is flagged for
              focused human re-verification.
            </p>
          </div>
          <span className="role-pill">{tasks.data?.length ?? 0} ACTIVE TASKS</span>
        </div>

        {tasks.isLoading ? (
          <div className="loading-state">Loading re-review work items…</div>
        ) : !tasks.data || tasks.data.length === 0 ? (
          <div className="success-state" style={{ margin: "1rem" }}>
            All approved assets are up-to-date with current facts and policies. No re-reviews pending.
          </div>
        ) : (
          <div style={{ padding: "1rem", display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            {tasks.data.map((task) => (
              <div
                key={task.id}
                style={{
                  background: "rgba(255, 82, 82, 0.05)",
                  borderLeft: "3px solid #FF5252",
                  padding: "0.85rem 1rem",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                    <strong>{task.title}</strong>
                    <span style={{ fontSize: "0.75rem", color: "#888" }}>({task.channel})</span>
                    <span
                      style={{
                        background: "#FF5252",
                        color: "#fff",
                        padding: "1px 6px",
                        fontSize: "0.68rem",
                        fontWeight: 700,
                      }}
                    >
                      DRIFT IMPACT
                    </span>
                  </div>
                  <div style={{ fontSize: "0.8rem", color: "#ccc", marginTop: "4px" }}>
                    {task.impact_summary}
                  </div>
                </div>
                <div style={{ display: "flex", gap: "0.5rem" }}>
                  <a
                    href={`/workspace/review?submission=${task.submission_id}`}
                    className="button outline-button"
                    style={{ fontSize: "0.75rem", padding: "0.4rem 0.8rem" }}
                  >
                    OPEN IN REVIEW STUDIO ↗
                  </a>
                  <button
                    className="button lime-button"
                    style={{ fontSize: "0.75rem", padding: "0.4rem 0.8rem" }}
                    disabled={resolveTask.isPending}
                    onClick={() => resolveTask.mutate(task.id)}
                  >
                    RESOLVE TASK ↗
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* SECTION 3: LINEAGE GRAPH VISUALIZATION */}
      <section className="panel">
        <div className="panel-head">
          <div>
            <div className="eyebrow">LINEAGE &amp; GOVERNANCE GRAPH</div>
            <h2>Evidence lineage &amp; change-impact graph</h2>
            <p>
              Traceable links from approved facts and policies down to the exact submissions
              and revisions that rely on them.
            </p>
          </div>
        </div>

        <div style={{ padding: "1rem" }}>
          <div
            style={{
              background: "#0a0a0a",
              border: "1px solid rgba(255, 255, 255, 0.08)",
              padding: "1rem",
              minHeight: "220px",
            }}
          >
            <div style={{ fontSize: "0.75rem", color: "#888", marginBottom: "0.75rem" }}>
              ACTIVE LINEAGE GRAPH ({graph.data?.nodes?.length ?? 0} nodes · {graph.data?.edges?.length ?? 0} relationships)
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
              {graph.data?.nodes?.map((node) => (
                <div
                  key={node.id}
                  style={{
                    padding: "0.4rem 0.75rem",
                    border: `1px solid ${
                      node.type === "fact"
                        ? "rgba(198, 255, 0, 0.4)"
                        : node.type === "policy"
                        ? "rgba(33, 150, 243, 0.4)"
                        : "rgba(255, 255, 255, 0.2)"
                    }`,
                    background:
                      node.type === "fact"
                        ? "rgba(198, 255, 0, 0.05)"
                        : node.type === "policy"
                        ? "rgba(33, 150, 243, 0.05)"
                        : "rgba(255, 255, 255, 0.02)",
                    fontSize: "0.78rem",
                    display: "flex",
                    alignItems: "center",
                    gap: "0.4rem",
                  }}
                >
                  <span
                    style={{
                      width: "6px",
                      height: "6px",
                      borderRadius: "50%",
                      background:
                        node.type === "fact"
                          ? "#C6FF00"
                          : node.type === "policy"
                          ? "#2196F3"
                          : "#fff",
                    }}
                  />
                  <strong>{node.label}</strong>
                  <span style={{ color: "#666", fontSize: "0.7rem" }}>[{node.type.toUpperCase()}]</span>
                </div>
              ))}
            </div>

            <div
              style={{
                marginTop: "1.25rem",
                borderTop: "1px solid rgba(255, 255, 255, 0.06)",
                paddingTop: "0.75rem",
                fontSize: "0.75rem",
                color: "#666",
              }}
            >
              Every revision and human decision retains immutable cryptographic linkage to the exact version of the fact and policy node governing it.
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
