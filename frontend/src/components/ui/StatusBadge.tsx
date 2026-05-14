import { humanizeStatus, statusTone } from "@/lib/format";

type StatusBadgeProps = {
  status: string;
};

export function StatusBadge({ status }: StatusBadgeProps) {
  return <span className={`badge badge-${statusTone(status)}`}>{humanizeStatus(status)}</span>;
}
