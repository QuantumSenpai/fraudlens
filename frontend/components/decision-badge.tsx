import { CircleCheck, CircleHelp, ShieldX } from "lucide-react";
import type { Decision } from "@/lib/types";

export function DecisionBadge({ value }: { value: Decision }): React.JSX.Element {
  const icon = value === "ALLOW" ? <CircleCheck size={15} /> : value === "REVIEW" ? <CircleHelp size={15} /> : <ShieldX size={15} />;
  return <span className={`decision-badge ${value.toLowerCase()}`}>{icon}{value}</span>;
}
