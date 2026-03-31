export default function AuthLoading() {
  return (
    <div className="mx-auto flex min-h-[60vh] max-w-md flex-col items-center justify-center px-6">
      <div className="w-full space-y-4">
        <div className="h-8 w-32 rounded animate-shimmer mx-auto" />
        <div className="h-10 w-full rounded animate-shimmer" />
        <div className="h-10 w-full rounded animate-shimmer" />
        <div className="h-10 w-full rounded animate-shimmer" />
      </div>
    </div>
  );
}
