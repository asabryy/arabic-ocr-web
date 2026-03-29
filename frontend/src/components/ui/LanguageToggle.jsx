import React from "react";
import { useTranslation } from "react-i18next";

const LanguageToggle = () => {
  const { i18n } = useTranslation();
  const isAr = i18n.language === "ar";

  return (
    <button
      onClick={() => i18n.changeLanguage(isAr ? "en" : "ar")}
      title={isAr ? "Switch to English" : "التبديل إلى العربية"}
      className="flex items-center justify-center w-8 h-8 rounded-lg text-sm font-semibold text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
    >
      {isAr ? "EN" : "ع"}
    </button>
  );
};

export default LanguageToggle;
