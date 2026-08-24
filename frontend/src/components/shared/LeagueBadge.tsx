export function LeagueBadge({ name, country }: { name: string; country?: string | null }) {
  return (
    <span className="inline-flex items-center rounded-full bg-muted px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
      {name}
      {country ? ` · ${country}` : ""}
    </span>
  )
}
