import { useState } from "react";
import { Card } from "../ui";
import LoginForm from "./LoginForm";
import RegisterForm from "./RegisterForm";

interface AuthTabsProps {
  /** Called after successful login/register. */
  onSuccess?: () => void;
}

export default function AuthTabs({ onSuccess }: AuthTabsProps) {
  const [activeTab, setActiveTab] = useState<"login" | "register">("login");

  return (
    <Card className="p-6">
      {/* Tab bar */}
      <div
        role="tablist"
        aria-label="认证方式"
        className="mb-5 flex border-b border-border"
      >
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "login"}
          onClick={() => setActiveTab("login")}
          className={`tab-btn flex-1 pb-2.5 text-sm font-medium ${
            activeTab === "login" ? "text-accent" : "text-text-secondary hover:text-text-primary"
          }`}
        >
          登录
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "register"}
          onClick={() => setActiveTab("register")}
          className={`tab-btn flex-1 pb-2.5 text-sm font-medium ${
            activeTab === "register" ? "text-accent" : "text-text-secondary hover:text-text-primary"
          }`}
        >
          注册
        </button>
      </div>

      {/* Tab panel */}
      <div role="tabpanel" className="animate-fade-in" key={activeTab}>
        {activeTab === "login" ? (
          <>
            <p className="mb-4 rounded-lg bg-amber-50 p-2 text-center text-xs text-amber-700 dark:bg-amber-950 dark:text-amber-400">
              内测阶段暂无验证码功能，若忘记密码直接新注册一个账号即可
            </p>
            <LoginForm onSuccess={onSuccess} />
          </>
        ) : (
          <>
            <p className="mb-4 rounded-lg bg-amber-50 p-2 text-center text-xs text-amber-700 dark:bg-amber-950 dark:text-amber-400">
              内测阶段暂无验证码功能，若忘记密码直接新注册一个账号即可
            </p>
            <RegisterForm onSuccess={onSuccess} />
          </>
        )}
      </div>
    </Card>
  );
}
