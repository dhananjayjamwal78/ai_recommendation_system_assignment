export function Spinner({ label = "Loading..." }) {
  return (
    <div className="center" style={{ padding: 24, gap: 10 }}>
      <div className="skel" style={{ width: 48, height: 48, borderRadius: 999 }} />
      <div className="sub">{label}</div>
    </div>
  );
}

export function Banner({ children }) {
  return <div className="banner">{children}</div>;
}

export function Empty({ hint = "Try changing your search or filters." }) {
  return (
    <div className="center" style={{ padding: 24, flexDirection: "column" }}>
      <div className="sub" style={{ fontSize: 14 }}>No results</div>
      <div className="sub" style={{ opacity: 0.8 }}>{hint}</div>
    </div>
  );
}
