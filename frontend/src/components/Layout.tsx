import { Link, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Layout() {
  const { isLoggedIn, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  return (
    <div className="min-h-screen flex flex-col">
      <nav
        style={{
          backgroundColor: "var(--bg-secondary)",
          borderBottom: "1px solid var(--border)",
        }}
        className="flex items-center justify-between px-6 py-3"
      >
        <Link to="/" className="text-lg font-bold no-underline" style={{ color: "var(--accent)" }}>
          TradeLens
        </Link>
        <div className="flex items-center gap-4">
          {isLoggedIn ? (
            <>
              <Link to="/upload" className="text-sm no-underline" style={{ color: "var(--text-secondary)" }}>
                上传
              </Link>
              <Link to="/history" className="text-sm no-underline" style={{ color: "var(--text-secondary)" }}>
                历史
              </Link>
              <button
                onClick={handleLogout}
                className="text-sm border-0 cursor-pointer bg-transparent"
                style={{ color: "var(--danger)" }}
              >
                退出
              </button>
            </>
          ) : (
            <>
              <Link to="/login" className="text-sm no-underline" style={{ color: "var(--text-secondary)" }}>
                登录
              </Link>
              <Link to="/register" className="text-sm no-underline" style={{ color: "var(--text-secondary)" }}>
                注册
              </Link>
            </>
          )}
        </div>
      </nav>
      <main className="flex-1">
        <Outlet />
      </main>
    </div>
  );
}
