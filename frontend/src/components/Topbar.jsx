export default function Topbar({ title, children }) {
  return (
    <div className="h-16 shrink-0 bg-surface border-b border-line flex items-center justify-between px-7">
      <h1 className="font-display text-[19px] font-semibold">{title}</h1>
      <div className="flex items-center gap-4">{children}</div>
    </div>
  );
}
