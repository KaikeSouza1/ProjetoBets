import { Inbox } from "lucide-react"
import type { ReactNode } from "react"

export function EmptyState({ message, icon }: { message: string; icon?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-md border border-dashed border-border py-12 text-center">
      <div className="text-muted-foreground">{icon ?? <Inbox className="h-6 w-6" />}</div>
      <p className="max-w-sm text-sm text-muted-foreground">{message}</p>
    </div>
  )
}
