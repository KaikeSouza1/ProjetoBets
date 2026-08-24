import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatPercent(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined) return "—"
  return `${(value * 100).toFixed(digits)}%`
}

export function formatSignedPercent(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined) return "—"
  const pct = value * 100
  return `${pct >= 0 ? "+" : ""}${pct.toFixed(digits)}%`
}

export function formatOdd(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—"
  return value.toFixed(2)
}

export function formatDateTime(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })
}

export function formatTime(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })
}
