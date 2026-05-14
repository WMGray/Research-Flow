import { Link } from "react-router-dom";
import { TopBar } from "@/components/layout/TopBar";

type Props = {
  title: string;
};

export function PlaceholderPage({ title }: Props) {
  return (
    <>
      <TopBar current={title} title={title} />
      <main className="page">
        <div className="placeholder-card">
          <span className="placeholder-kicker">Paper MVP</span>
          <h1>{title}</h1>
          <p>本轮只落地 HomePage 和本地文献库脚本能力，其余模块暂时保留为占位页。</p>
          <Link className="ghost-button" to="/">
            返回 Home
          </Link>
        </div>
      </main>
    </>
  );
}
