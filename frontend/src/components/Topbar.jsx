const styles = {
  topbar: { height: 64, background: "var(--surface)", borderBottom: "1px solid var(--border)", display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 28px", flexShrink: 0 },
  title: { fontFamily: "var(--font-display)", fontSize: 19, fontWeight: 600 },
};

export default function Topbar({ title, children }) {
  return (
    <div style={styles.topbar}>
      <h1 style={styles.title}>{title}</h1>
      <div style={{ display: "flex", alignItems: "center", gap: 16 }}>{children}</div>
    </div>
  );
}
