"use client";

import { RefreshCw } from "lucide-react";

export default function ErrorPage({ reset }: { error: Error; reset: () => void }): React.JSX.Element {
  return <main id="main" className="error-page"><div><p className="eyebrow">UNAVAILABLE</p><h1>Something interrupted the page.</h1><p>Try loading this view again. No payment action has been confirmed here.</p><button className="button button-dark" type="button" onClick={reset}><RefreshCw size={18} />Retry page</button></div></main>;
}
