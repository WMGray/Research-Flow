import { Search } from "lucide-react";

import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

type FilterSearchProps = {
  value: string;
  placeholder: string;
  label: string;
  className?: string;
  onChange: (value: string) => void;
};

export function FilterSearch({ className, label, onChange, placeholder, value }: FilterSearchProps) {
  return (
    <label className={cn("relative block", className)}>
      <span className="sr-only">{label}</span>
      <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
      <Input
        aria-label={label}
        className="pl-9"
        placeholder={placeholder}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}
