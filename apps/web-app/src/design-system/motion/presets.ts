/**
 * Motion presets for the authenticated app (Framer Motion / motion library).
 * Public pages use GSAP instead.
 */
export const appMotion = {
  fadeIn: {
    initial: { opacity: 0 },
    animate: { opacity: 1 },
    transition: { duration: 0.15 },
  },
  slideUp: {
    initial: { opacity: 0, y: 12 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.2, ease: [0.25, 0.46, 0.45, 0.94] },
  },
  modalEnter: {
    initial: { opacity: 0, scale: 0.96 },
    animate: { opacity: 1, scale: 1 },
    exit: { opacity: 0, scale: 0.98 },
    transition: { duration: 0.2 },
  },
  staggerContainer: {
    animate: { transition: { staggerChildren: 0.05 } },
  },
  staggerChild: {
    initial: { opacity: 0, y: 8 },
    animate: { opacity: 1, y: 0 },
  },
  buttonPress: {
    whileTap: { scale: 0.97 },
  },
  cardHover: {
    whileHover: { y: -2 },
    transition: { duration: 0.2 },
  },
} as const;
