import { Link } from "react-router-dom";
import { Button } from "../components/ui";
import { useAuth } from "../context/AuthContext";

const DESTINATIONS = [
  { to: "/", label: "首页", desc: "回到 TradeDoctor" },
  { to: "/upload", label: "上传交割单", desc: "开始一次新的分析" },
  { to: "/history", label: "历史分析", desc: "查看过往分析记录" },
  { to: "/login", label: "登录 / 注册", desc: "管理你的账号" },
];

export default function NotFound() {
  const { isLoggedIn } = useAuth();
  // 登录用户看不到"登录/注册"入口
  const items = DESTINATIONS.filter(
    (d) => isLoggedIn || d.to !== "/login"
  );

  return (
    <div className="flex min-h-[70vh] flex-col items-center justify-center px-4 py-12 text-center">
      <div className="mb-4 text-6xl">🔍</div>
      <h1 className="mb-2 text-2xl font-semibold">404</h1>
      <p className="mb-8 text-text-secondary">页面不存在</p>

      <div className="mb-6">
        <Link to="/">
          <Button variant="primary">返回首页</Button>
        </Link>
      </div>

      <div className="w-full max-w-md">
        <p className="mb-3 text-xs uppercase tracking-wider text-text-secondary">
          或前往
        </p>
        <ul className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {items.map((d) => (
            <li key={d.to}>
              <Link
                to={d.to}
                className="block rounded-lg border border-border bg-bg-secondary/60 px-4 py-3 text-left transition-colors hover:border-accent/40 hover:bg-bg-tertiary no-underline"
              >
                <div className="text-sm font-medium text-text-primary">
                  {d.label}
                </div>
                <div className="mt-0.5 text-xs text-text-secondary">
                  {d.desc}
                </div>
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
