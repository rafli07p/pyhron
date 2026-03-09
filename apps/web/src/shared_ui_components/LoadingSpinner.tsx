interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  label?: string;
}

const sizeMap = {
  sm: 'w-4 h-4',
  md: 'w-8 h-8',
  lg: 'w-12 h-12',
};

export default function LoadingSpinner({ size = 'md', label }: LoadingSpinnerProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-12">
      <div
        className={`${sizeMap[size]} border-2 border-bloomberg-border border-t-bloomberg-accent rounded-full animate-spin`}
      />
      {label && (
        <span className="text-xs text-bloomberg-text-muted font-mono">{label}</span>
      )}
    </div>
  );
}
