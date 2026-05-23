import Navbar from "@/components/layout/Navbar";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-surface-1">
      <Navbar />
      <main className="pt-14">{children}</main>
    </div>
  );
}
