import { AlertTriangle } from "lucide-react"

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-md border border-negative-bg bg-negative-bg py-12 text-center">
      <AlertTriangle className="h-6 w-6 text-negative" />
      <p className="max-w-sm text-sm text-negative">{message}</p>
      {onRetry && (
        <button onClick={onRetry} className="text-xs font-medium text-negative underline underline-offset-2">
          Tentar de novo
        </button>
      )}
    </div>
  )
}
