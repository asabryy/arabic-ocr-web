import React from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { AlignRight, LayoutDashboard, Zap, Cloud, ArrowRight, FileText } from "lucide-react";
import Logo from "../assets/Logo.jsx";
import LanguageToggle from "../components/ui/LanguageToggle";
import DarkModeToggle from "../components/ui/DarkModeToggle";

const FEATURES = [
  { icon: AlignRight,      key: "rtl",    num: "01" },
  { icon: LayoutDashboard, key: "layout", num: "02" },
  { icon: Zap,             key: "gpu",    num: "03" },
  { icon: Cloud,           key: "cloud",  num: "04" },
];

const STEPS = [
  { num: "01", key: "upload" },
  { num: "02", key: "process" },
  { num: "03", key: "download" },
];

function LandingNavbar({ openLogin, openRegister }) {
  const { t } = useTranslation();
  return (
    <header className="fixed top-0 inset-x-0 z-50 h-12 bg-white/90 dark:bg-zinc-950/90 backdrop-blur-md border-b border-zinc-200 dark:border-zinc-800">
      <div className="max-w-6xl mx-auto h-full flex items-center justify-between px-6">
        <Link to="/" className="flex items-center gap-2">
          <Logo className="h-5 w-auto fill-zinc-900 dark:fill-white" />
        </Link>
        <div className="flex items-center gap-4">
          <nav className="hidden sm:flex items-center gap-5 text-sm text-zinc-500 dark:text-zinc-400">
            <Link to="/pricing" className="hover:text-zinc-900 dark:hover:text-zinc-100 transition-colors">
              {t("nav.pricing")}
            </Link>
          </nav>
          <div className="flex items-center gap-1">
            <LanguageToggle />
            <DarkModeToggle />
          </div>
          <div className="flex items-center gap-2">
            {openLogin && (
              <button onClick={openLogin}
                className="hidden sm:block text-sm text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 transition-colors">
                {t("nav.signIn")}
              </button>
            )}
            {openRegister && (
              <button onClick={openRegister} className="btn-primary text-xs px-3 py-1.5">
                {t("nav.getStarted")}
              </button>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}

function LandingPage({ openLogin, openRegister }) {
  const { t } = useTranslation();

  return (
    <div className="min-h-screen bg-white dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100">
      <LandingNavbar openLogin={openLogin} openRegister={openRegister} />

      {/* ── HERO: asymmetric split ── */}
      <section className="pt-12 min-h-screen flex flex-col">
        <div className="flex-1 max-w-6xl mx-auto w-full px-6 flex flex-col lg:flex-row">

          {/* Left column — text */}
          <div className="flex flex-col justify-center py-20 lg:py-0 lg:w-[52%] lg:pr-16">
            <div className="flex items-center gap-2 mb-8">
              <div className="h-px w-8 bg-indigo-500" />
              <span className="section-label text-indigo-500">{t("landing.badge")}</span>
            </div>
            <h1 className="text-5xl sm:text-6xl lg:text-7xl font-bold leading-[1.04] tracking-tight mb-8">
              {t("landing.heroTitle1")}{" "}
              <span className="text-indigo-500">{t("landing.heroTitle2")}</span>
              <br />
              {t("landing.heroTitle3")}
            </h1>
            <p className="text-base text-zinc-500 dark:text-zinc-400 leading-relaxed mb-10 max-w-md">
              {t("landing.heroSubtitle")}
            </p>
            <div className="flex flex-col sm:flex-row gap-3">
              <button onClick={openRegister} className="btn-primary gap-2 px-6 py-2.5 text-sm group">
                {t("landing.heroCta")}
                <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-0.5 rtl:rotate-180" />
              </button>
              <button onClick={openLogin} className="btn-secondary px-6 py-2.5 text-sm">
                {t("landing.heroSignIn")}
              </button>
            </div>
            <p className="text-xs text-zinc-400 dark:text-zinc-600 mt-4">{t("landing.heroNote")}</p>
          </div>

          {/* Right column — app preview panel */}
          <div className="lg:w-[48%] flex items-center py-12 lg:py-20">
            <div className="w-full">
              {/* Thin top accent */}
              <div className="h-0.5 w-full bg-indigo-500 mb-0" />
              <div className="studio-card overflow-hidden shadow-xl shadow-zinc-200/60 dark:shadow-black/40">
                {/* Mini toolbar */}
                <div className="flex items-center gap-3 px-4 py-2.5 border-b border-zinc-100 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900">
                  <div className="flex gap-1.5">
                    <div className="w-2.5 h-2.5 rounded-full bg-zinc-300 dark:bg-zinc-600" />
                    <div className="w-2.5 h-2.5 rounded-full bg-zinc-300 dark:bg-zinc-600" />
                    <div className="w-2.5 h-2.5 rounded-full bg-zinc-300 dark:bg-zinc-600" />
                  </div>
                  <div className="flex-1 h-4 bg-zinc-200 dark:bg-zinc-700 rounded-sm max-w-[160px]" />
                  <div className="w-16 h-4 bg-indigo-100 dark:bg-indigo-500/20 rounded-sm" />
                </div>
                {/* Content area */}
                <div className="p-4 space-y-3">
                  {/* Stat row — inline, no big cards */}
                  <div className="grid grid-cols-4 divide-x divide-zinc-100 dark:divide-zinc-800 border border-zinc-100 dark:border-zinc-800">
                    {[
                      { v: "12", l: "Total",     c: "text-zinc-900 dark:text-zinc-100" },
                      { v: "1",  l: "Converting",c: "text-indigo-500" },
                      { v: "10", l: "Done",      c: "text-emerald-600 dark:text-emerald-400" },
                      { v: "1",  l: "Failed",    c: "text-red-500" },
                    ].map(({ v, l, c }) => (
                      <div key={l} className="px-3 py-2.5 text-center">
                        <p className={`text-xl font-bold tabular-nums ${c}`}>{v}</p>
                        <p className="text-[9px] text-zinc-400 uppercase tracking-wide mt-0.5">{l}</p>
                      </div>
                    ))}
                  </div>
                  {/* Column headers */}
                  <div className="grid grid-cols-[1fr_auto_auto] gap-3 px-3 py-1.5 border-b border-zinc-100 dark:border-zinc-800">
                    <span className="section-label">File</span>
                    <span className="section-label">Status</span>
                    <span className="section-label">Action</span>
                  </div>
                  {/* Rows */}
                  {[
                    { name: "تقرير المالية 2024.pdf", w: 140, status: "done",       statusCls: "status-done" },
                    { name: "عقد الخدمات.pdf",         w: 110, status: "converting", statusCls: "status-processing" },
                    { name: "السياسة العامة.pdf",       w: 125, status: "pending",   statusCls: "status-pending" },
                  ].map(({ name, w, statusCls, status }, i) => (
                    <div key={name} className="grid grid-cols-[1fr_auto_auto] gap-3 items-center px-3 py-2.5 border-b border-zinc-100 dark:border-zinc-800 last:border-0">
                      <div className="flex items-center gap-2">
                        <FileText className="w-3.5 h-3.5 text-zinc-300 dark:text-zinc-600 shrink-0" />
                        <div className="h-2.5 rounded-sm bg-zinc-200 dark:bg-zinc-700" style={{ width: w }} />
                      </div>
                      <span className={statusCls}>{status}</span>
                      <div className={`h-5 w-14 rounded-sm ${i === 0 ? 'bg-emerald-50 dark:bg-emerald-500/10' : i === 2 ? 'bg-indigo-50 dark:bg-indigo-500/10' : 'bg-zinc-100 dark:bg-zinc-800'}`} />
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Full-width rule ── */}
      <div className="border-t border-zinc-200 dark:border-zinc-800" />

      {/* ── FEATURES: numbered editorial list ── */}
      <section className="py-24 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="flex items-baseline gap-6 mb-12">
            <span className="section-label">{t("landing.featuresTitle")}</span>
            <div className="flex-1 h-px bg-zinc-200 dark:bg-zinc-800" />
          </div>
          <div className="grid gap-0 divide-y divide-zinc-100 dark:divide-zinc-800 border-t border-zinc-100 dark:border-zinc-800">
            {FEATURES.map(({ icon: Icon, key, num }) => (
              <div key={key}
                className="grid grid-cols-[3rem_1fr_auto] sm:grid-cols-[4rem_1fr_1fr] items-start gap-6 py-8 group hover:bg-zinc-50/60 dark:hover:bg-zinc-900/40 px-2 -mx-2 transition-colors">
                <span className="text-3xl font-bold text-zinc-100 dark:text-zinc-800 select-none group-hover:text-zinc-200 dark:group-hover:text-zinc-700 transition-colors tabular-nums">{num}</span>
                <div>
                  <h3 className="font-semibold text-base mb-1">{t(`landing.features.${key}.title`)}</h3>
                  <p className="text-sm text-zinc-500 dark:text-zinc-400 leading-relaxed sm:max-w-xs">
                    {t(`landing.features.${key}.desc`)}
                  </p>
                </div>
                <div className="hidden sm:flex justify-end">
                  <div className="w-9 h-9 border border-zinc-200 dark:border-zinc-700 flex items-center justify-center group-hover:border-indigo-300 dark:group-hover:border-indigo-600 group-hover:bg-indigo-50 dark:group-hover:bg-indigo-500/10 transition-colors">
                    <Icon className="w-4 h-4 text-zinc-400 group-hover:text-indigo-500 transition-colors" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Full-width rule ── */}
      <div className="border-t border-zinc-200 dark:border-zinc-800" />

      {/* ── HOW IT WORKS: large numbers as typographic anchors ── */}
      <section className="py-24 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="flex items-baseline gap-6 mb-12">
            <span className="section-label">{t("landing.howTitle")}</span>
            <div className="flex-1 h-px bg-zinc-200 dark:bg-zinc-800" />
          </div>
          <div className="grid sm:grid-cols-3 gap-0 divide-y sm:divide-y-0 sm:divide-x divide-zinc-200 dark:divide-zinc-800">
            {STEPS.map(({ num, key }) => (
              <div key={key} className="py-8 sm:px-10 first:sm:pl-0 last:sm:pr-0">
                <div className="text-[4.5rem] font-extrabold leading-none text-zinc-100 dark:text-zinc-800/80 select-none mb-6 tabular-nums">
                  {num}
                </div>
                <h3 className="font-semibold mb-2">{t(`landing.steps.${key}.title`)}</h3>
                <p className="text-sm text-zinc-500 dark:text-zinc-400 leading-relaxed">
                  {t(`landing.steps.${key}.body`)}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA: full-width dark band ── */}
      <section className="bg-zinc-950 dark:bg-black py-20 px-6">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-start sm:items-center justify-between gap-8">
          <div>
            <h2 className="text-3xl sm:text-4xl font-bold text-white leading-tight mb-3">
              {t("landing.ctaTitle")}
            </h2>
            <p className="text-zinc-400 max-w-sm leading-relaxed text-sm">
              {t("landing.ctaSubtitle")}
            </p>
          </div>
          <div className="shrink-0">
            <button onClick={openRegister} className="btn-primary px-8 py-3 text-base gap-2 group">
              {t("landing.ctaButton")}
              <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-0.5 rtl:rotate-180" />
            </button>
          </div>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="border-t border-zinc-200 dark:border-zinc-800 py-6 px-6">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Logo className="h-4 w-auto fill-zinc-400 dark:fill-zinc-600" />
            <span className="text-xs text-zinc-400 dark:text-zinc-600">
              {t("landing.footerCopy", { year: new Date().getFullYear() })}
            </span>
          </div>
          <div className="flex items-center gap-5 text-xs text-zinc-400 dark:text-zinc-600">
            <Link to="/pricing" className="hover:text-zinc-700 dark:hover:text-zinc-300 transition-colors">
              {t("nav.pricing")}
            </Link>
            <button onClick={openLogin} className="hover:text-zinc-700 dark:hover:text-zinc-300 transition-colors">
              {t("nav.signIn")}
            </button>
            <button onClick={openRegister} className="text-indigo-500 hover:text-indigo-600 transition-colors font-medium">
              {t("nav.getStarted")}
            </button>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default LandingPage;
