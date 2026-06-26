import { useNavigate, Link } from "react-router-dom";
import { Card } from "../components/ui";
import RegisterForm from "../components/auth/RegisterForm";

export default function Register() {
  const navigate = useNavigate();

  return (
    <div className="flex min-h-[80vh] items-center justify-center px-4">
      <Card className="w-full max-w-sm p-8">
        <h1 className="mb-6 text-center text-xl font-semibold">注册</h1>
        <p className="mb-4 rounded-lg bg-amber-50 p-2 text-center text-xs text-amber-700 dark:bg-amber-950 dark:text-amber-400">
          内测阶段暂无验证码功能，若忘记密码直接新注册一个账号即可
        </p>
        <RegisterForm onSuccess={() => navigate("/upload")} />
        <p className="mt-4 text-center text-sm text-text-secondary">
          已有账号？<Link to="/login" className="text-accent hover:underline">登录</Link>
        </p>
      </Card>
    </div>
  );
}
