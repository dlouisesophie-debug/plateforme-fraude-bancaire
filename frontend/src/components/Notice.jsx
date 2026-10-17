const TONES = {
  danger: "bg-danger-soft text-danger",
  success: "bg-success-soft text-success",
  info: "bg-brand-soft text-brand",
};

export default function Notice({ tone = "danger", children, className = "" }) {
  if (!children) return null;
  return (
    <div role={tone === "danger" ? "alert" : "status"} className={`rounded-xl px-4 py-3 text-sm ${TONES[tone]} ${className}`}>
      {children}
    </div>
  );
}
