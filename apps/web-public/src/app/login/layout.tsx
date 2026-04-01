export default function LoginLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-[80vh] items-center justify-center px-6 py-12">
      {children}
    </div>
  );
}
