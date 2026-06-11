import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Landing() {
  const { isLoggedIn } = useAuth();

  return (
    <div className="flex flex-col items-center justify-center min-h-[80vh] px-4 text-center">
      <h1 className="text-4xl font-bold mb-4">
        TradingJournalAnalyzer
      </h1>
      <p className="text-lg mb-8" style={{ color: "var(--text-secondary)", maxWidth: "480px" }}>
        上传您的交易交割单，AI 将分析您的交易行为，找出亏损原因并生成改善建议。
      </p>
      <div className="flex gap-4">
        {isLoggedIn ? (
          <Link
            to="/upload"
            style={{
              backgroundColor: "var(--accent)",
              color: "#fff",
              borderRadius: "8px",
              padding: "12px 32px",
              textDecoration: "none",
            }}
            className="text-sm font-medium"
          >
            开始分析
          </Link>
        ) : (
          <>
            <Link
              to="/login"
              style={{
                backgroundColor: "var(--accent)",
                color: "#fff",
                borderRadius: "8px",
                padding: "12px 32px",
                textDecoration: "none",
              }}
              className="text-sm font-medium"
            >
              登录
            </Link>
            <Link
              to="/register"
              style={{
                backgroundColor: "var(--bg-tertiary)",
                color: "var(--text-primary)",
                border: "1px solid var(--border)",
                borderRadius: "8px",
                padding: "12px 32px",
                textDecoration: "none",
              }}
              className="text-sm font-medium"
            >
              注册
            </Link>
          </>
        )}
      </div>
      <div
        className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-16"
        style={{ maxWidth: "720px" }}
      >
        {[
          { title: "上传交割单", desc: "支持 CSV / Excel 格式，自动识别券商", icon: "📄" },
          { title: "行为分析", desc: "识别追涨、抄底、波段等交易模式", icon: "🔍" },
          { title: "AI 诊断", desc: "生成个性化交易行为诊断报告", icon: "🤖" },
        ].map((item) => (
          <div
            key={item.title}
            style={{
              backgroundColor: "var(--bg-secondary)",
              borderRadius: "12px",
              border: "1px solid var(--border)",
            }}
            className="p-6 text-left"
          >
            <div className="text-2xl mb-3">{item.icon}</div>
            <h3 className="font-medium mb-2">{item.title}</h3>
            <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
              {item.desc}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
