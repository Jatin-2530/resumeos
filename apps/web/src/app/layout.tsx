import type { Metadata } from "next";
import { Toaster } from "react-hot-toast";
import QueryProvider from "@/components/providers/QueryProvider";
import "./globals.css";

export const metadata: Metadata = {
  title: "ResumeOS — Constraint-Aware Resume Intelligence",
  description:
    "AI-powered resume optimization that preserves your formatting while maximizing ATS compatibility and recruiter impact.",
  keywords: ["resume", "AI", "ATS", "optimization", "MBA", "career"],
  openGraph: {
    title: "ResumeOS",
    description: "Constraint-Aware Resume Intelligence Platform",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
      </head>
      <body>
        <QueryProvider>
          {children}
          <Toaster
            position="bottom-right"
            toastOptions={{
              duration: 4000,
              style: {
                background: "#111827",
                color: "#F9FAFB",
                fontSize: "14px",
                borderRadius: "8px",
              },
            }}
          />
        </QueryProvider>
      </body>
    </html>
  );
}
