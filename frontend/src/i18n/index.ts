import { createI18n } from 'vue-i18n'
import en from './locales/en.json'
import it from './locales/it.json'

const messages = {
  en,
  it
}

// Persist language choice
const savedLocale = localStorage.getItem('locale')
const browserLocale = navigator.language.split('-')[0]
const defaultLocale = savedLocale || (messages[browserLocale as keyof typeof messages] ? browserLocale : 'en')

const i18n = createI18n({
  legacy: false, // use Composition API
  locale: defaultLocale,
  fallbackLocale: 'en',
  messages,
})

export default i18n

export function setLanguage(locale: string) {
  if (messages[locale as keyof typeof messages]) {
    i18n.global.locale.value = locale as any
    localStorage.setItem('locale', locale)
    document.documentElement.setAttribute('lang', locale)
  }
}
