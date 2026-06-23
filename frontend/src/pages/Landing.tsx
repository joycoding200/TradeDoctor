import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { Button, Card } from "../components/ui";

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
          <Link to="/upload">
            <Button>开始分析</Button>
          </Link>
        ) : (
          <>
            <Link to="/login">
              <Button>登录</Button>
            </Link>
            <Link to="/register">
              <Button variant="outline">注册</Button>
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
          <Card key={item.title} className="p-6 text-left">
            <div className="text-2xl mb-3">{item.icon}</div>
            <h3 className="font-medium mb-2">{item.title}</h3>
            <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
              {item.desc}
            </p>
          </Card>
        ))}
      </div>
    </div>
  );
}
