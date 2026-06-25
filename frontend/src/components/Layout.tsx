import { useState, useEffect } from "react";
import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { useConfirm } from "../context/ConfirmContext";
import { clearTrades } from "../api/upload";
import { getMe, updateNickname } from "../api/auth";
import { Input } from "./ui";

export default function Layout() {
  const { isLoggedIn, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const toast = useToast();
  const confirmDialog = useConfirm();
  const [menuOpen, setMenuOpen] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [nickname, setNickname] = useState("");
  const [editingNick, setEditingNick] = useState(false);
  const [nickInput, setNickInput] = useState("");
  const [nickSaving, setNickSaving] = useState(false);

  useEffect(() => {
    if (isLoggedIn) {
      getMe().then((u) => setNickname(u.nickname || "")).catch(() => {});
    }
  }, [isLoggedIn]);

  // Close mobile nav on route change
  useEffect(() => {
    setMobileNavOpen(false);
    setMenuOpen(false);
  }, [location.pathname]);

  const handleSaveNick = async () => {
    const v = nickInput.trim();
    if (!v || v.length < 2 || v.length > 20) return;
    setNickSaving(true);
    try {
      await updateNickname(v);
      setNickname(v);
      setEditingNick(false);
      toast.addToast("success", "昵称已更新");
    } catch (err) {
      toast.addToast("error", err instanceof Error ? err.message : "修改失败");
    } finally {
      setNickSaving(false);
    }
  };

  const handleLogout = () => {
    logout();
    toast.addToast("info", "已退出登录");
    navigate("/");
  };

  const handleClear = async () => {
    const ok = await confirmDialog.confirm({
      title: "清空全部数据",
      message: "将永久删除所有交易记录、分析结果、AI 报告和原始文件。此操作不可撤销，确定继续？",
      confirmText: "永久删除",
      cancelText: "取消",
      variant: "danger",
    });
    if (!ok) return;
    setMenuOpen(false);
    setClearing(true);
    try {
      await clearTrades();
      toast.addToast("success", "所有交易数据已永久删除");
      navigate("/upload");
    } catch (err) {
      toast.addToast("error", err instanceof Error ? err.message : "清空失败");
    } finally {
      setClearing(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col">
      <nav className="relative flex items-center justify-between border-b border-border bg-bg-secondary px-4 py-3 md:px-6">
        <div className="flex items-center gap-3">
          <Link to="/" className="text-lg font-bold no-underline text-accent">
            TradeDoctor
          </Link>
        </div>

        {/* Desktop nav */}
        <div className="hidden items-center gap-4 md:flex">
          {isLoggedIn ? (
            <>
              <Link to="/upload" className="text-sm no-underline text-text-secondary transition-colors hover:text-accent">
                上传
              </Link>
              <div className="relative">
                <button
                  type="button"
                  onClick={() => setMenuOpen(!menuOpen)}
                  aria-expanded={menuOpen}
                  aria-haspopup="true"
                  aria-label="账户菜单"
                  className="flex h-8 w-8 cursor-pointer items-center justify-center rounded-full border-0 bg-bg-tertiary p-0 transition-colors hover:brightness-125 focus-ring"
                >
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-text-secondary">
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
                      className="absolute right-0 top-full z-20 min-w-40 animate-fade-in rounded-lg border border-border bg-bg-secondary py-1 shadow-lg">
                      {/* Nickname display + edit */}
                      <div className="px-4 py-2 text-sm text-text-secondary">
                        {editingNick ? (
                          <div className="flex items-center gap-1">
                            <Input
                              value={nickInput}
                              onChange={(e) => setNickInput(e.target.value)}
                              maxLength={20}
                              placeholder="输入昵称"
                              autoFocus
                              className="!w-24 !px-1 !py-1 !text-xs"
                            />
                            <button type="button" onClick={handleSaveNick} disabled={nickSaving}
                              className="cursor-pointer border-0 bg-transparent p-0 text-xs text-accent disabled:opacity-50">
                              {nickSaving ? "..." : "保存"}
                            </button>
                          </div>
                        ) : (
                          <div className="flex items-center gap-2">
                            <span>{nickname || "未设置昵称"}</span>
                            <button type="button" onClick={() => { setNickInput(nickname); setEditingNick(true); }}
                              className="cursor-pointer border-0 bg-transparent p-0 text-[11px] text-text-secondary hover:text-accent">
                              ✎
                            </button>
                          </div>
                        )}
                      </div>
                      <div className="mx-0 my-1 border-t border-border" />
                      <button
                        type="button"
                        onClick={() => { navigate("/history"); setMenuOpen(false); }}
                        className="w-full cursor-pointer border-0 bg-transparent px-4 py-2 text-left text-sm text-text-primary transition-colors hover:bg-bg-tertiary focus-ring"
                      >
                        历史报告
                      </button>
                      <button
                        type="button"
                        onClick={handleClear}
                        disabled={clearing}
                        className="w-full cursor-pointer border-0 bg-transparent px-4 py-2 text-left text-sm text-warning transition-colors hover:bg-bg-tertiary disabled:opacity-50 focus-ring"
                      >
                        {clearing ? "清空中..." : "清空数据"}
                      </button>
                      <div className="mx-0 my-1 border-t border-border" />
                      <button
                        type="button"
                        onClick={handleLogout}
                        className="w-full cursor-pointer border-0 bg-transparent px-4 py-2 text-left text-sm text-danger transition-colors hover:bg-bg-tertiary focus-ring"
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
              <Link to="/login" className="text-sm no-underline text-text-secondary transition-colors hover:text-accent">
                登录
              </Link>
              <Link to="/register" className="text-sm no-underline text-text-secondary transition-colors hover:text-accent">
                注册
              </Link>
            </>
          )}
        </div>

        {/* Mobile hamburger */}
        <button
          type="button"
          className="cursor-pointer border-0 bg-transparent p-1 text-text-secondary md:hidden focus-ring"
          onClick={() => setMobileNavOpen(!mobileNavOpen)}
          aria-label="菜单"
          aria-expanded={mobileNavOpen}
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            {mobileNavOpen ? (
              <>
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </>
            ) : (
              <>
                <line x1="3" y1="6" x2="21" y2="6" />
                <line x1="3" y1="12" x2="21" y2="12" />
                <line x1="3" y1="18" x2="21" y2="18" />
              </>
            )}
          </svg>
        </button>
      </nav>

      {/* Mobile nav dropdown — slideDown animation */}
      {mobileNavOpen && (
        <div className="animate-slide-down border-b border-border bg-bg-secondary px-4 py-3 md:hidden">
          {isLoggedIn ? (
            <div className="flex flex-col gap-2">
              <div className="px-2 py-1 text-xs text-text-secondary">
                {nickname || "未设置昵称"}
              </div>
              <Link to="/upload" className="block px-2 py-1 text-sm no-underline text-text-primary">
                上传
              </Link>
              <Link to="/history" className="block px-2 py-1 text-sm no-underline text-text-primary">
                历史报告
              </Link>
              <button onClick={handleClear} disabled={clearing}
                className="border-0 bg-transparent px-2 py-1 text-left text-sm text-warning disabled:opacity-50">
                {clearing ? "清空中..." : "清空数据"}
              </button>
              <div className="my-1 border-t border-border" />
              <button onClick={handleLogout}
                className="border-0 bg-transparent px-2 py-1 text-left text-sm text-danger">
                退出登录
              </button>
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              <Link to="/login" className="block px-2 py-1 text-sm no-underline text-text-primary">
                登录
              </Link>
              <Link to="/register" className="block px-2 py-1 text-sm no-underline text-text-primary">
                注册
              </Link>
            </div>
          )}
        </div>
      )}

      <main className="flex-1">
        <Outlet />
      </main>
    </div>
  );
}
