import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import en from "./locales/en.json";
import ar from "./locales/ar.json";

const lng = localStorage.getItem("lang") || "en";

i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    ar: { translation: ar },
  },
  lng,
  fallbackLng: "en",
  interpolation: { escapeValue: false },
});

const applyLang = (lang) => {
  const dir = lang === "ar" ? "rtl" : "ltr";
  document.documentElement.dir = dir;
  document.documentElement.lang = lang;
  localStorage.setItem("lang", lang);
};

i18n.on("languageChanged", applyLang);
applyLang(lng);

export default i18n;
