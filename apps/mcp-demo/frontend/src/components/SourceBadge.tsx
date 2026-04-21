/** 工具来源的色彩统一约定：native 蓝、MCP 绿。整份应用共用。 */
export function sourceClasses(source: string): {
  border: string;
  bg: string;
  badge: string;
  dot: string;
  label: string;
} {
  if (source === "native") {
    return {
      border: "border-sky-300",
      bg: "bg-sky-50",
      badge: "bg-sky-100 text-sky-800 border-sky-300",
      dot: "bg-sky-500",
      label: "native",
    };
  }
  // mcp:<server>
  return {
    border: "border-emerald-300",
    bg: "bg-emerald-50",
    badge: "bg-emerald-100 text-emerald-800 border-emerald-300",
    dot: "bg-emerald-500",
    label: source,
  };
}

export function SourceBadge({ source }: { source: string }) {
  const c = sourceClasses(source);
  return (
    <span
      className={
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider " +
        c.badge
      }
    >
      <span className={"h-1.5 w-1.5 rounded-full " + c.dot} />
      {c.label}
    </span>
  );
}
