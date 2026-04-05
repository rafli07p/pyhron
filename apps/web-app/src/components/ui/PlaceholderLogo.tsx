interface PlaceholderLogoProps {
  name: string;
  width?: number;
  height?: number;
  className?: string;
}

export function PlaceholderLogo({ name, width = 120, height = 30, className }: PlaceholderLogoProps) {
  return (
    <div className={`inline-flex items-center justify-center ${className ?? ''}`} style={{ width, height }}
         title={`Logo: ${name} — replace with real SVG`}>
      <span className="font-mono text-[10px] uppercase tracking-wider text-white/20">{name}</span>
    </div>
  );
}
