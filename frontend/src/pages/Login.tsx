import { useNavigate, Link } from "react-router-dom";
import { Card } from "../components/ui";
import LoginForm from "../components/auth/LoginForm";

export default function Login() {
  const navigate = useNavigate();

  return (
    <div className="flex min-h-[80vh] items-center justify-center px-4">
      <Card className="w-full max-w-sm p-8">
        <h1 className="mb-6 text-center text-xl font-semibold">登录</h1>
        <p className="mb-4 rounded-lg bg-amber-50 p-2 text-center text-xs text-amber-700 dark:bg-amber-950 dark:text-amber-400">
          内测阶段暂无验证码功能，若忘记密码直接新注册一个账号即可
        </p>
        <LoginForm onSuccess={() => navigate("/upload")} />
        <p className="mt-3 text-center text-xs text-text-secondary">
          忘记密码？内测阶段直接重新注册即可
        </p>
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
