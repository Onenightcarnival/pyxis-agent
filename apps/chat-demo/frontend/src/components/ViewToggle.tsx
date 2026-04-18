import type { ViewMode } from "../App";

interface Props {
  value: ViewMode;
  onChange: (v: ViewMode) => void;
}

export function ViewToggle({ value, onChange }: Props) {
  const options: { key: ViewMode; label: string; hint: string }[] = [
    { key: "chat", label: "Chat", hint: "{role, content} 风格气泡" },
    { key: "inspect", label: "Inspect", hint: "schema 字段逐个亮起" },
  ];
  return (
    <div
      className="inline-flex items-center gap-1 rounded-lg border border-zinc-200 bg-white p-1 shadow-sm"
      role="tablist"
    >
      {options.map((opt) => {
        const active = value === opt.key;
        return (
          <button
            key={opt.key}
            role="tab"
            aria-selected={active}
            onClick={() => onChange(opt.key)}
            title={opt.hint}
            className={
              "px-3 py-1 text-sm rounded-md transition-colors " +
              (active
                ? "bg-zinc-900 text-white"
                : "text-zinc-600 hover:bg-zinc-100")
            }
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
