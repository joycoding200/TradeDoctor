import { useState, useEffect } from "react";
import { useNavigate, Link, useSearchParams } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { useToast } from "../../context/ToastContext";
import { login as loginApi } from "../../api/auth";
import { Input, Button } from "../ui";

interface LoginFormProps {
  /** Called after successful login. Default: navigate("/upload"). */
  onSuccess?: () => void;
}

export default function LoginForm({ onSuccess }: LoginFormProps) {
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

    if (!account.trim()) { setError("请输入邮箱或手机号"); return; }
    if (!password) { setError("请输入密码"); return; }

    setLoading(true);
    try {
      const token = await loginApi(account, password);
      login(token);
      toast.addToast("success", "登录成功");
      if (onSuccess) {
        onSuccess();
      } else {
        navigate("/upload");
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "登录失败";
      setError(msg);
      toast.addToast("error", msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      {error && (
        <div className="rounded-lg bg-danger/10 p-3 text-sm text-danger">
          <p className="mb-1">{error}</p>
          {(error.includes("账号或密码") || error.includes("账号不存在")) && (
            <p className="text-text-secondary">
              还没有账号？<Link to="/register" className="text-accent underline">立即注册</Link>
            </p>
          )}
          {error.includes("密码") && !error.includes("账号") && (
            <p className="text-text-secondary">
              忘记密码？内测阶段直接 <Link to="/register" className="text-accent underline">重新注册</Link> 即可
            </p>
          )}
        </div>
      )}
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
          className="absolute right-3 top-1/2 -translate-y-1/2 cursor-pointer border-0 bg-transparent p-1 text-text-secondary hover:text-text-primary focus-ring"
        >
          {showPw ? (
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94" />
              <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19" />
              <line x1="1" y1="1" x2="23" y2="23" />
            </svg>
          ) : (
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
              <circle cx="12" cy="12" r="3" />
            </svg>
          )}
        </button>
      </div>
      <Button type="submit" disabled={loading}>
        {loading ? "登录中..." : "登录"}
      </Button>
    </form>
  );
}
