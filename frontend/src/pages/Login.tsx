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
    <div className="flex min-h-[80vh] items-center justify-center px-4">
      <Card className="w-full max-w-sm p-8">
        <h1 className="mb-6 text-center text-xl font-semibold">登录</h1>
        {error && (
          <div className="mb-4 rounded-lg bg-danger/10 p-3 text-sm text-danger">
            {error}
          </div>
        )}
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <Input
            type="text"
            placeholder="邮箱或手机号"
            value={account}
            onChange={(e) => setAccount(e.target.value)}
            required
          />
          <div className="relative">
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
              className="absolute right-2.5 top-1/2 -translate-y-1/2 cursor-pointer border-0 bg-transparent p-1 text-base leading-none text-text-secondary focus-ring"
            >
              {showPw ? "🙈" : "👁"}
            </button>
          </div>
          <Button type="submit" disabled={loading}>
            {loading ? "登录中..." : "登录"}
          </Button>
        </form>
        <p className="mt-4 text-center text-sm text-text-secondary">
          没有账号？{" "}
          <Link to="/register" className="text-accent hover:underline">
            注册
          </Link>
        </p>
      </Card>
    </div>
  );
}
