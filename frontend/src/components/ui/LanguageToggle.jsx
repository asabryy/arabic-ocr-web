import React from "react";
import { useTranslation } from "react-i18next";

const LanguageToggle = () => {
  const { i18n } = useTranslation();
  const isAr = i18n.language === "ar";

  return (
    <button
      onClick={() => i18n.changeLanguage(isAr ? "en" : "ar")}
      title={isAr ? "Switch to English" : "التبديل إلى العربية"}
      className="flex items-center justify-center w-7 h-7 text-xs font-semibold text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 transition-colors"
    >
      {isAr ? "EN" : "ع"}
    </button>
  );
};

export default LanguageToggle;
