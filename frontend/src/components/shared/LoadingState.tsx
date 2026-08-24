export function LoadingState({ label = "Carregando..." }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-sm text-muted-foreground">
      <div className="h-5 w-5 animate-spin rounded-full border-2 border-border border-t-foreground" />
      {label}
    </div>
  )
}

export function CardSkeleton() {
  return <div className="h-24 animate-pulse rounded-md border border-border bg-muted" />
}
