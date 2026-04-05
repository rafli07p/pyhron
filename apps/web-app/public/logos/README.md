# Logo Assets

This directory holds partner/data-source logos used on the landing page.

## Swapping placeholder logos with real SVGs

1. Place your SVG files in this directory, e.g. `idx.svg`, `ojk.svg`, `bloomberg.svg`, etc.
2. Open `src/components/landing/TrustedBy.tsx`.
3. Replace each `<PlaceholderLogo>` with a Next.js `<Image>` or inline `<svg>`:

```tsx
import Image from 'next/image';

// Replace:
<PlaceholderLogo name="IDX" width={80} />

// With:
<Image src="/logos/idx.svg" alt="IDX" width={80} height={30} />
```

4. Once all placeholders are replaced, you can remove the `PlaceholderLogo` component from
   `src/components/ui/PlaceholderLogo.tsx` if it is no longer used elsewhere.

## Guidelines

- Use monochrome (white or white/20 opacity) SVGs for dark backgrounds.
- Keep file sizes under 5 KB per logo.
- Preferred dimensions: width 70-120px, height ~30px.
