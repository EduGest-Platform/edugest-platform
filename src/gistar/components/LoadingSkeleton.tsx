export function LoadingSkeleton({ label, rows = 3 }: { label: string; rows?: number }) {
  return (
    <div role="status" className="grid gap-3 rounded-xl border border-line bg-white p-4">
      <p className="text-sm text-muted">{label}</p>
      <div aria-hidden="true" className="grid gap-3 motion-safe:animate-pulse">
        {Array.from({ length: rows }, (_, index) => (
          <div key={index} className="grid gap-2 rounded-lg border border-line p-3">
            <div className="h-3 w-2/5 rounded bg-line" />
            <div className="h-3 w-4/5 rounded bg-mist" />
          </div>
        ))}
      </div>
    </div>
  )
}
