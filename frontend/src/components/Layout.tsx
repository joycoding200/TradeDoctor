import { useState } from "react";
import { Link, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { clearTrades } from "../api/upload";

export default function Layout() {
  const { isLoggedIn, logout } = useAuth();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const [clearing, setClearing] = useState(false);

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  const handleClear = async () => {
    if (!window.confirm("确认清空所有历史交易记录？此操作不可撤销。")) return;
    setMenuOpen(false);
    setClearing(true);
    try {
      await clearTrades();
      navigate("/upload");
    } catch (err) {
      alert(err instanceof Error ? err.message : "清空失败");
    } finally {
      setClearing(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      <nav
        style={{
          backgroundColor: "var(--bg-secondary)",
          borderBottom: "1px solid var(--border)",
        }}
        className="flex items-center justify-between px-6 py-3 relative"
      >
        <Link to="/" className="text-lg font-bold no-underline" style={{ color: "var(--accent)" }}>
          TradingJournalAnalyzer
        </Link>
        <div className="flex items-center gap-4">
          {isLoggedIn ? (
            <>
              <Link to="/upload" className="text-sm no-underline" style={{ color: "var(--text-secondary)" }}>
                上传
              </Link>
              <div className="relative">
                <button
                  onClick={() => setMenuOpen(!menuOpen)}
                  className="flex items-center justify-center border-0 cursor-pointer bg-transparent p-0"
                  style={{ width: 32, height: 32, borderRadius: "50%", backgroundColor: "var(--bg-tertiary)" }}
                >
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--text-secondary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                    <circle cx="12" cy="7" r="4" />
                  </svg>
                </button>
                {menuOpen && (
                  <>
                    <div
                      className="fixed inset-0 z-10"
                      onClick={() => setMenuOpen(false)}
                    />
                    <div
                      className="absolute right-0 top-full mt-1 z-20 rounded-lg shadow-lg py-1"
                      style={{
                        backgroundColor: "var(--bg-secondary)",
                        border: "1px solid var(--border)",
                        minWidth: 140,
                      }}
                    >
                      <button
                        onClick={() => { navigate("/history"); setMenuOpen(false); }}
                        className="w-full text-left text-sm px-4 py-2 border-0 cursor-pointer bg-transparent hover:bg-[var(--bg-tertiary)] transition-colors"
                        style={{ color: "var(--text-primary)" }}
                      >
                        历史报告
                      </button>
                      <button
                        onClick={handleClear}
                        disabled={clearing}
                        className="w-full text-left text-sm px-4 py-2 border-0 cursor-pointer bg-transparent hover:bg-[var(--bg-tertiary)] transition-colors"
                        style={{ color: "var(--warning)", opacity: clearing ? 0.5 : 1 }}
                      >
                        {clearing ? "清空中..." : "清空数据"}
                      </button>
                      <div style={{ borderTop: "1px solid var(--border)", margin: "4px 0" }} />
                      <button
                        onClick={handleLogout}
                        className="w-full text-left text-sm px-4 py-2 border-0 cursor-pointer bg-transparent hover:bg-[var(--bg-tertiary)] transition-colors"
                        style={{ color: "var(--danger)" }}
                      >
                        退出登录
                      </button>
                    </div>
                  </>
                )}
              </div>
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
