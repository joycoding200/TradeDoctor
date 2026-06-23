import { Link } from "react-router-dom";
import { Button } from "../components/ui";

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[70vh] px-4 text-center">
      <div className="text-6xl mb-4">🔍</div>
      <h1 className="text-2xl font-semibold mb-2">404</h1>
      <p className="mb-6" style={{ color: "var(--text-secondary)" }}>
        页面不存在
      </p>
      <Link to="/">
        <Button variant="primary">返回首页</Button>
      </Link>
    </div>
  );
}
