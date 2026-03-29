import React from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  AlignRight,
  LayoutDashboard,
  Zap,
  Cloud,
  ChevronRight,
  Tag,
  FileText,
} from "lucide-react";
import Logo from "../assets/Logo.jsx";
import LanguageToggle from "../components/ui/LanguageToggle";
import DarkModeToggle from "../components/ui/DarkModeToggle";

const FEATURES = [
  { icon: AlignRight, key: "rtl" },
  { icon: LayoutDashboard, key: "layout" },
  { icon: Zap, key: "gpu" },
  { icon: Cloud, key: "cloud" },
];

const STEPS = [
  { num: "01", key: "upload" },
  { num: "02", key: "process" },
  { num: "03", key: "download" },
];

function LandingNavbar({ openLogin, openRegister }) {
  const { t } = useTranslation();
  return (
    <header className="fixed top-0 inset-x-0 z-50 h-14 glass border-b border-zinc-200/60 dark:border-zinc-800/60">
      <div className="max-w-6xl mx-auto h-full grid grid-cols-2 sm:grid-cols-3 items-center px-5">
        <div>
          <Link to="/" className="flex items-center gap-2">
            <Logo className="h-6 w-auto fill-zinc-900 dark:fill-white" />
          </Link>
        </div>
        <nav className="hidden sm:flex justify-center">
          <Link
            to="/pricing"
            className="px-3 py-1.5 text-sm text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
          >
            {t("nav.pricing")}
          </Link>
        </nav>
        <div className="flex justify-end items-center gap-1">
          <LanguageToggle />
          <DarkModeToggle />
          {openLogin && (
            <button
              onClick={openLogin}
              className="hidden sm:block px-3 py-1.5 text-sm font-medium text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 transition-colors"
            >
              {t("nav.signIn")}
            </button>
          )}
          {openRegister && (
            <>
              <button
                onClick={openRegister}
                className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg bg-indigo-500 hover:bg-indigo-600 text-white transition-colors"
              >
                {t("nav.getStarted")}
              </button>
              <button
                onClick={openRegister}
                className="sm:hidden inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg bg-indigo-500 hover:bg-indigo-600 text-white transition-colors"
              >
                {t("nav.start")}
              </button>
            </>
          )}
        </div>
      </div>
    </header>
  );
}

function LandingPage({ openLogin, openRegister }) {
  const { t } = useTranslation();

  return (
    <div className="min-h-screen bg-white dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100 font-sans">
      <LandingNavbar openLogin={openLogin} openRegister={openRegister} />

      {/* Hero */}
      <section className="relative pt-32 pb-24 px-4 overflow-hidden">
        <div className="absolute inset-0 -z-10 hero-glow" />
        <div className="absolute inset-0 -z-10 [background-image:linear-gradient(to_right,rgba(99,102,241,0.05)_1px,transparent_1px),linear-gradient(to_bottom,rgba(99,102,241,0.05)_1px,transparent_1px)] [background-size:64px_64px]" />
        <div className="max-w-3xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-600 dark:text-indigo-400 text-xs font-medium mb-8">
            <Tag className="w-3 h-3" />
            {t("landing.badge")}
          </div>
          <h1 className="text-5xl sm:text-6xl lg:text-7xl font-extrabold leading-[1.08] tracking-tight mb-6">
            {t("landing.heroTitle1")}{" "}
            <span className="text-gradient">{t("landing.heroTitle2")}</span>
            <br />
            {t("landing.heroTitle3")}
          </h1>
          <p className="text-lg text-zinc-500 dark:text-zinc-400 max-w-xl mx-auto mb-10 leading-relaxed">
            {t("landing.heroSubtitle")}
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <button
              onClick={openRegister}
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3 text-base font-medium rounded-lg bg-indigo-500 hover:bg-indigo-600 text-white transition-colors group"
            >
              {t("landing.heroCta")}
              <ChevronRight className="w-4 h-4 transition-transform group-hover:translate-x-0.5 rtl:rotate-180" />
            </button>
            <button
              onClick={openLogin}
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3 text-base font-medium rounded-lg border border-zinc-200 dark:border-zinc-700 text-zinc-600 dark:text-zinc-400 hover:bg-zinc-50 dark:hover:bg-zinc-800/60 hover:text-zinc-900 dark:hover:text-zinc-100 transition-colors"
            >
              {t("landing.heroSignIn")}
            </button>
          </div>
          <p className="text-xs text-zinc-400 dark:text-zinc-600 mt-4">{t("landing.heroNote")}</p>
        </div>

        {/* Dashboard mockup */}
        <div className="mt-16 max-w-3xl mx-auto">
          <div className="glass-card rounded-2xl shadow-xl shadow-indigo-500/5 dark:shadow-black/40 overflow-hidden">
            <div className="flex items-center gap-1.5 px-4 py-3 border-b border-zinc-200/80 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900/60">
              <div className="w-3 h-3 rounded-full bg-red-400" />
              <div className="w-3 h-3 rounded-full bg-amber-400" />
              <div className="w-3 h-3 rounded-full bg-emerald-400" />
              <div className="flex-1 mx-4">
                <div className="h-5 bg-zinc-200 dark:bg-zinc-700 rounded-md max-w-[220px] mx-auto" />
              </div>
            </div>
            <div className="p-6 grid gap-4">
              <div className="grid grid-cols-3 gap-4">
                {[
                  { label: "Total documents", val: "12", color: "bg-indigo-500/10" },
                  { label: "Converting", val: "1", color: "bg-amber-500/10" },
                  { label: "Converted", val: "10", color: "bg-emerald-500/10" },
                ].map(({ label, val, color }) => (
                  <div key={label} className="glass-card rounded-xl p-4 flex items-center gap-3">
                    <div className={`w-8 h-8 rounded-lg ${color} shrink-0`} />
                    <div>
                      <div className="text-lg font-bold">{val}</div>
                      <div className="text-[11px] text-zinc-400 leading-tight">{label}</div>
                    </div>
                  </div>
                ))}
              </div>
              <div className="glass-card rounded-xl p-4 space-y-2">
                {[
                  { name: "تقرير المالية 2024.pdf", status: "done", w: "w-56" },
                  { name: "عقد الخدمات.pdf", status: "processing", w: "w-40" },
                  { name: "السياسة العامة.pdf", status: "pending", w: "w-48" },
                ].map(({ name, status, w }) => (
                  <div
                    key={name}
                    className="flex items-center justify-between py-2 border-b border-zinc-100 dark:border-zinc-800 last:border-0"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-7 h-7 rounded-lg bg-indigo-500/10 flex items-center justify-center">
                        <FileText className="w-3.5 h-3.5 text-indigo-400" />
                      </div>
                      <div className={`h-3 ${w} bg-zinc-200 dark:bg-zinc-700 rounded`} />
                    </div>
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                        status === "done"
                          ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                          : status === "processing"
                          ? "bg-indigo-500/10 text-indigo-600 dark:text-indigo-400"
                          : "bg-zinc-200/80 dark:bg-zinc-800 text-zinc-400"
                      }`}
                    >
                      {status === "done" ? "Done" : status === "processing" ? "Converting" : "Pending"}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-24 px-4 bg-zinc-50 dark:bg-zinc-900/40">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-14">
            <h2 className="text-3xl sm:text-4xl font-bold mb-4">{t("landing.featuresTitle")}</h2>
            <p className="text-zinc-500 dark:text-zinc-400 max-w-lg mx-auto">
              {t("landing.featuresSubtitle")}
            </p>
          </div>
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {FEATURES.map(({ icon: Icon, key }) => (
              <div
                key={key}
                className="glass-card rounded-2xl p-5 hover:shadow-md hover:shadow-indigo-500/5 dark:hover:shadow-black/30 hover:border-indigo-200 dark:hover:border-indigo-500/20 transition-all duration-200 group"
              >
                <div className="w-9 h-9 rounded-xl bg-indigo-500/10 flex items-center justify-center mb-4 group-hover:bg-indigo-500/15 transition-colors">
                  <Icon className="w-4 h-4 text-indigo-500 dark:text-indigo-400" />
                </div>
                <h3 className="font-semibold text-sm mb-2">{t(`landing.features.${key}.title`)}</h3>
                <p className="text-xs text-zinc-500 dark:text-zinc-400 leading-relaxed">
                  {t(`landing.features.${key}.desc`)}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="py-24 px-4">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-14">
            <h2 className="text-3xl sm:text-4xl font-bold mb-4">{t("landing.howTitle")}</h2>
            <p className="text-zinc-500 dark:text-zinc-400">{t("landing.howSubtitle")}</p>
          </div>
          <div className="grid gap-8 sm:grid-cols-3">
            {STEPS.map(({ num, key }) => (
              <div key={key} className="relative">
                <div className="text-6xl font-black text-zinc-100 dark:text-zinc-800 select-none mb-4 leading-none">
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

      {/* CTA */}
      <section className="py-24 px-4">
        <div className="max-w-2xl mx-auto text-center">
          <div className="glass-card rounded-3xl p-12 relative overflow-hidden">
            <div className="absolute inset-0 -z-10 bg-gradient-to-br from-indigo-500/5 via-transparent to-violet-500/5" />
            <h2 className="text-3xl sm:text-4xl font-bold mb-4">{t("landing.ctaTitle")}</h2>
            <p className="text-zinc-500 dark:text-zinc-400 mb-8 max-w-sm mx-auto">
              {t("landing.ctaSubtitle")}
            </p>
            <button
              onClick={openRegister}
              className="inline-flex items-center gap-2 px-6 py-3 text-base font-medium rounded-lg bg-indigo-500 hover:bg-indigo-600 text-white transition-colors group"
            >
              {t("landing.ctaButton")}
              <ChevronRight className="w-4 h-4 transition-transform group-hover:translate-x-0.5 rtl:rotate-180" />
            </button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-zinc-200 dark:border-zinc-800 py-8 px-4">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <Logo className="h-5 w-auto fill-zinc-400 dark:fill-zinc-600" />
            <span className="text-sm text-zinc-400 dark:text-zinc-600">
              {t("landing.footerCopy", { year: new Date().getFullYear() })}
            </span>
          </div>
          <div className="flex items-center gap-5 text-sm text-zinc-400 dark:text-zinc-600">
            <Link to="/pricing" className="hover:text-zinc-700 dark:hover:text-zinc-300 transition-colors">
              {t("nav.pricing")}
            </Link>
            <button
              onClick={openLogin}
              className="hover:text-zinc-700 dark:hover:text-zinc-300 transition-colors"
            >
              {t("nav.signIn")}
            </button>
            <button
              onClick={openRegister}
              className="hover:text-zinc-700 dark:hover:text-zinc-300 transition-colors"
            >
              {t("nav.getStarted")}
            </button>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default LandingPage;
