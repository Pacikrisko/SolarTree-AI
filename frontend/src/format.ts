import {locale} from './language'

const numbers = new Map<string, Intl.NumberFormat>()
const clocks = new Map<string, Intl.DateTimeFormat>()

export function formatNum(value:number, decimals=0) {
  const language = locale()
  const key = language + '/' + decimals
  let formatter = numbers.get(key)
  if (!formatter) {
    formatter = new Intl.NumberFormat(language, {minimumFractionDigits:decimals, maximumFractionDigits:decimals})
    numbers.set(key, formatter)
  }
  return formatter.format(value)
}

export function formatTime(iso:string) {
  const language = locale()
  let formatter = clocks.get(language)
  if (!formatter) {
    formatter = new Intl.DateTimeFormat(language, {hour:'2-digit', minute:'2-digit'})
    clocks.set(language, formatter)
  }
  const date = new Date(iso)
  return Number.isNaN(date.getTime()) ? '—' : formatter.format(date)
}
