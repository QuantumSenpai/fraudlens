import Link from "next/link";
export function Brand(): React.JSX.Element {
  return <Link className="brand" href="/" aria-label="FraudLens home"><svg className="brand-mark" viewBox="0 0 32 32" fill="none" aria-hidden="true"><path d="M4 27V5h23M4 16h18M16 27V16" stroke="currentColor" strokeWidth="4"/><path d="m22 22 5 5m-5 0 5-5" stroke="currentColor" strokeWidth="3"/></svg><span>Fraud<span>Lens</span></span></Link>;
}
