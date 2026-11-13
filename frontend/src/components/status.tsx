export function Status({ status }: { status: string }) {
  const label = status.replaceAll("_", " ");
  return <span className={`status status-${status}`}>{label}</span>;
}
