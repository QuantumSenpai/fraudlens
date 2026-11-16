import { ImageResponse } from "next/og";

export const size = { width: 1200, height: 630 };
export const alt = "FraudLens: signals become ALLOW, REVIEW, or BLOCK decisions";
export const contentType = "image/png";

export default function OpenGraphImage(): ImageResponse {
  return new ImageResponse(<div style={{ width: "100%", height: "100%", background: "#161616", color: "#FEF8E8", display: "flex", alignItems: "center", padding: 80, fontFamily: "sans-serif", position: "relative" }}><div style={{ display: "flex", flexDirection: "column" }}><div style={{ fontSize: 30, color: "#F44A22", marginBottom: 48 }}>FRAUDLENS</div><div style={{ fontSize: 86, fontWeight: 700, letterSpacing: -5, lineHeight: 1, display: "flex", flexDirection: "column" }}><span>From signal</span><span>to decision.</span></div><div style={{ fontSize: 25, marginTop: 42, color: "#d2ccc0" }}>Clear fraud decisions before test payments.</div></div><div style={{ display: "flex", flexDirection: "column", position: "absolute", right: 70, top: 160, width: 300 }}>{["ALLOW", "REVIEW", "BLOCK"].map((label,index) => <div key={label} style={{display:"flex",padding:24,borderBottom:"1px solid #A8AAAC",background:index === 1 ? "#F44A22" : "transparent",color:index === 1 ? "#161616" : "#FEF8E8",fontSize:30}}>{label}</div>)}</div></div>, size);
}
