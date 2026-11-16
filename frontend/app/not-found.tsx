import Link from "next/link";
import { ArrowLeft } from "lucide-react";

export default function NotFound(): React.JSX.Element {
  return <main id="main" className="error-page"><div><p className="eyebrow">404</p><h1>Page not found.</h1><p>The address may have changed. Return to the FraudLens home page.</p><Link className="button button-dark" href="/"><ArrowLeft size={18} />Back home</Link></div></main>;
}
