import {
  Archive,
  BookOpen,
  CommandIcon,
  Compass,
  Download,
  FileText,
  FolderPen,
  LayoutDashboard,
  Search,
  Settings,
  Sparkles,
  Tags,
} from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { Input } from "@/components/ui/input";
import { useDialog } from "@/components/ui/DialogProvider";

const navigationItems = [
  { label: "打开概览", to: "/", icon: LayoutDashboard },
  { label: "Open Discover", to: "/discover", icon: Compass },
  { label: "Open Library", to: "/library", icon: BookOpen },
  { label: "Open Uncategorized", to: "/uncategorized", icon: Tags },
  { label: "打开归档", to: "/archive", icon: Archive },
  { label: "打开设置", to: "/settings", icon: Settings },
] as const;

export function TopBar() {
  const navigate = useNavigate();
  const { notify } = useDialog();
  const [open, setOpen] = useState(false);

  const showPlaceholder = (action: string) => {
    notify({
      title: `${action} 暂未接入`,
      message: "入口已预留；后端或当前选择上下文接入后即可执行。",
      confirmLabel: "知道了",
    });
  };

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b bg-background/95 px-4 backdrop-blur supports-[backdrop-filter]:bg-background/80">
      <div className="relative hidden min-w-0 flex-1 md:block">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          aria-label="全局搜索"
          className="h-9 max-w-xl border-border bg-card pl-9 text-sm"
          placeholder="搜索论文、作者、venue、标签..."
          readOnly
          onFocus={() => setOpen(true)}
        />
      </div>

      <Button className="md:hidden" size="icon" variant="outline" onClick={() => setOpen(true)}>
        <Search className="h-4 w-4" />
        <span className="sr-only">搜索</span>
      </Button>

      <Button className="gap-2" size="sm" variant="outline" onClick={() => setOpen(true)}>
        <CommandIcon className="h-4 w-4" />
        <span className="hidden sm:inline">Command</span>
      </Button>

      <Button className="gap-2" size="sm" onClick={() => showPlaceholder("Import Paper")}>
        <Download className="h-4 w-4" />
        <span>Import Paper</span>
      </Button>

      <CommandDialog open={open} onOpenChange={setOpen}>
        <CommandInput placeholder="输入页面或操作..." />
        <CommandList>
          <CommandEmpty>没有匹配项</CommandEmpty>
          <CommandGroup heading="导航">
            {navigationItems.map((item) => {
              const Icon = item.icon;
              return (
                <CommandItem
                  key={item.to}
                  onSelect={() => {
                    navigate(item.to);
                    setOpen(false);
                  }}
                >
                  <Icon className="h-4 w-4" />
                  <span>{item.label}</span>
                </CommandItem>
              );
            })}
          </CommandGroup>
          <CommandGroup heading="操作">
            <ActionCommand icon={Download} label="Import Paper" onSelect={() => showPlaceholder("Import Paper")} />
            <ActionCommand icon={Search} label="New Search" onSelect={() => navigate("/discover")} />
            <ActionCommand icon={FileText} label="Parse Selected" onSelect={() => showPlaceholder("Parse Selected")} />
            <ActionCommand icon={Sparkles} label="Generate Note" onSelect={() => showPlaceholder("Generate Note")} />
            <ActionCommand icon={FolderPen} label="Set Domain" onSelect={() => navigate("/uncategorized")} />
            <ActionCommand icon={Archive} label="Archive Selected" onSelect={() => showPlaceholder("Archive Selected")} />
          </CommandGroup>
        </CommandList>
      </CommandDialog>
    </header>
  );
}

function ActionCommand({ icon: Icon, label, onSelect }: { icon: typeof Download; label: string; onSelect: () => void }) {
  return (
    <CommandItem
      onSelect={() => {
        onSelect();
      }}
    >
      <Icon className="h-4 w-4" />
      <span>{label}</span>
    </CommandItem>
  );
}
