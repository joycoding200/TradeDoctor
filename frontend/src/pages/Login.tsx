import { useState, useEffect } from "react";
import { useNavigate, Link, useSearchParams } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { login as loginApi } from "../api/auth";
import { Card, Input, Button } from "../components/ui";

export default function Login() {
  const [account, setAccount] = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();
  const [searchParams] = useSearchParams();

  useEffect(() => {
    if (searchParams.get("expired") === "1") {
      setError("登录已过期，请重新登录");
    }
  }, [searchParams]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const token = await loginApi(account, password);
      login(token);
      toast.addToast("success", "登录成功");
      navigate("/upload");
    } catch (err) {
      setError(err instanceof Error ? err.message : "登录失败");
      toast.addToast("error", err instanceof Error ? err.message : "登录失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-[80vh] px-4">
      <Card className="w-full max-w-sm p-8">
        <h1 className="text-xl font-semibold mb-6 text-center">登录</h1>
        {error && (
          <div
            className="text-sm mb-4 p-3 rounded-lg"
            style={{ backgroundColor: "rgba(248,113,113,0.1)", color: "var(--danger)" }}
          >
            {error}
          </div>
        )}
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <Input
            type="email"
            placeholder="邮箱或手机号"
            value={account}
            onChange={(e) => setAccount(e.target.value)}
            required
          />
          <div style={{ position: "relative" }}>
            <Input
              type={showPw ? "text" : "password"}
              placeholder="密码"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="pr-10"
            />
            <button
              type="button"
              onClick={() => setShowPw(!showPw)}
              aria-label={showPw ? "隐藏密码" : "显示密码"}
              style={{
                position: "absolute", right: 10, top: "50%", transform: "translateY(-50%)",
                background: "none", border: "none", cursor: "pointer",
                color: "var(--text-secondary)", fontSize: 16, padding: 4, lineHeight: 1,
              }}
            >
              {showPw ? "🙈" : "👁"}
            </button>
          </div>
          <Button type="submit" disabled={loading}>
            {loading ? "登录中..." : "登录"}
          </Button>
        </form>
        <p className="text-sm mt-4 text-center" style={{ color: "var(--text-secondary)" }}>
          没有账号？{" "}
          <Link to="/register" style={{ color: "var(--accent)" }}>
            注册
          </Link>
        </p>
      </Card>
    </div>
  );
}
