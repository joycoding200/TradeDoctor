import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { Button, Card } from "../components/ui";
import AuthTabs from "../components/auth/AuthTabs";

/* ─── Inline SVG icons ───────────────────────────────────────────────────── */
const DocIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
    <polyline points="14 2 14 8 20 8" />
    <line x1="8" y1="13" x2="16" y2="13" />
    <line x1="8" y1="17" x2="13" y2="17" />
  </svg>
);

const ChartIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <line x1="18" y1="20" x2="18" y2="10" />
    <line x1="12" y1="20" x2="12" y2="4" />
    <line x1="6" y1="20" x2="6" y2="14" />
    <line x1="2" y1="20" x2="22" y2="20" />
  </svg>
);

const SparkleIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 2l2.4 7.2h7.6l-6 4.8 2.4 7.2-6.4-4.8-6.4 4.8 2.4-7.2-6-4.8h7.6z" />
  </svg>
);

const LockIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
    <path d="M7 11V7a5 5 0 0 1 10 0v4" />
  </svg>
);

const CheckIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="mt-px shrink-0 text-success">
    <polyline points="20 6 9 17 4 12" />
  </svg>
);

const CheckIconSmall = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="mt-px shrink-0 text-success">
    <polyline points="20 6 9 17 4 12" />
  </svg>
);

/* ─── Data ───────────────────────────────────────────────────────────────── */
const FEATURES = [
  { title: "上传交割单", desc: "支持 CSV / Excel 格式，自动识别券商", Icon: DocIcon },
  { title: "行为分析", desc: "识别追涨、抄底、波段等交易模式", Icon: ChartIcon },
  { title: "AI 诊断", desc: "生成个性化交易行为诊断报告", Icon: SparkleIcon },
];

const HIGHLIGHTS = [
  "上传交割单，自动识别券商格式",
  "识别追涨、抄底、波段等交易模式",
  "AI 生成个性化交易诊断报告",
];

const TRUST_ITEMS = [
  "交割单仅用于分析，不上传第三方",
  "可一键彻底删除所有数据",
  "默认不进入案例库",
  "仅在您授权后匿名贡献案例",
];

/* ═══════════════════════════════════════════════════════════════════════════ */
export default function Landing() {
  const { isLoggedIn } = useAuth();

  return (
    <div className="px-4 py-8 sm:py-12">
      {/* ═══ Hero Section ════════════════════════════════════════════════════ */}
      {isLoggedIn ? (
        /* ── Logged in: centered CTA ─────────────────────────────────────── */
        <div className="flex min-h-[60vh] flex-col items-center justify-center text-center">
          <div className="animate-fade-in-up">
            <h1 className="mb-3 text-4xl font-extrabold tracking-tight sm:text-5xl">
              <span className="bg-gradient-to-r from-blue-400 via-accent to-purple-400 bg-clip-text text-transparent">
                TradeDoctor
              </span>
            </h1>
            <p className="mx-auto mb-10 max-w-[500px] text-base leading-relaxed text-text-secondary sm:text-lg">
              上传您的交易交割单，AI 将分析您的交易行为，找出亏损原因并生成改善建议。
            </p>
          </div>
          <div
            className="animate-fade-in-up flex flex-wrap items-center justify-center gap-3"
            style={{ animationDelay: "150ms" }}
          >
            <Link to="/upload">
              <Button className="shadow-lg shadow-accent/25">开始分析</Button>
            </Link>
          </div>
        </div>
      ) : (
        /* ── Logged out: two-column hero ────────────────────────────────── */
        <div className="mx-auto grid max-w-5xl items-start gap-8 md:grid-cols-[1fr_400px]">
          {/* Left: Branding */}
          <div className="animate-fade-in-up pt-2 text-center md:pt-8 md:text-left">
            <h1 className="mb-3 text-4xl font-extrabold tracking-tight sm:text-5xl">
              <span className="bg-gradient-to-r from-blue-400 via-accent to-purple-400 bg-clip-text text-transparent">
                TradeDoctor
              </span>
            </h1>
            <p className="mx-auto mb-8 max-w-[500px] text-base leading-relaxed text-text-secondary md:mx-0 md:text-lg">
              上传您的交易交割单，AI 将分析您的交易行为，找出亏损原因并生成改善建议。
            </p>

            {/* Feature highlights (visible on md+) */}
            <div className="hidden space-y-3 md:block">
              {HIGHLIGHTS.map((text) => (
                <div key={text} className="flex items-center gap-3 text-sm text-text-secondary">
                  <CheckIconSmall />
                  <span>{text}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Right: Auth form */}
          <div
            className="animate-fade-in-up"
            style={{ animationDelay: "150ms" }}
          >
            <AuthTabs onSuccess={() => {}} />
          </div>
        </div>
      )}

      {/* ═══ Feature Cards (always visible) ══════════════════════════════════ */}
      <div className="mx-auto mt-20 grid w-full max-w-[780px] grid-cols-1 gap-5 sm:grid-cols-3">
        {FEATURES.map(({ title, desc, Icon }, i) => (
          <div
            key={title}
            className="animate-fade-in-up"
            style={{ animationDelay: `${isLoggedIn ? 300 : 600 + i * 150}ms` }}
          >
            <Card className="group border-border/60 p-6 text-left transition-all duration-300 hover:-translate-y-1.5 hover:border-accent/40 hover:shadow-xl hover:shadow-accent/5">
              <div className="mb-4 inline-flex rounded-xl bg-accent/10 p-2.5 text-accent transition-colors duration-300 group-hover:bg-accent/15">
                <Icon />
              </div>
              <h3 className="mb-2 text-[15px] font-semibold text-text-primary">
                {title}
              </h3>
              <p className="text-sm leading-relaxed text-text-secondary">
                {desc}
              </p>
            </Card>
          </div>
        ))}
      </div>

      {/* ═══ Trust Section (always visible) ══════════════════════════════════ */}
      <div
        className="animate-fade-in-up mx-auto mt-20 w-full max-w-[600px] rounded-2xl border border-border/60 bg-bg-secondary/80 p-6 text-left backdrop-blur-sm transition-shadow duration-300 hover:shadow-lg md:p-8"
        style={{ animationDelay: "1200ms" }}
      >
        <div className="mb-5 flex items-center gap-3">
          <span className="inline-flex rounded-xl bg-success/10 p-2 text-success">
            <LockIcon />
          </span>
          <h2 className="text-base font-semibold text-text-primary">
            你的数据，你做主
          </h2>
        </div>
        <ul className="space-y-3">
          {TRUST_ITEMS.map((item) => (
            <li
              key={item}
              className="flex items-start gap-2.5 text-sm text-text-secondary"
            >
              <CheckIcon />
              <span>{item}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
