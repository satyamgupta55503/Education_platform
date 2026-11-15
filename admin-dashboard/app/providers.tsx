"use client";
// app/providers.tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "react-hot-toast";
import { useState } from "react";

export default function Providers({ children }: { children: React.ReactNode }) {
  const [qc] = useState(
    () => new QueryClient({
      defaultOptions: {
        queries: { staleTime: 30_000, retry: 1, refetchOnWindowFocus: false },
      },
    })
  );
  return (
    <QueryClientProvider client={qc}>
      {children}
      <Toaster position="top-right" toastOptions={{
        duration: 3500,
        style: { borderRadius: "12px", fontSize: "13px",
          fontFamily: "'Sora', sans-serif",
          boxShadow: "0 4px 24px rgba(0,0,0,0.12)" },
        success: { iconTheme: { primary: "#059669", secondary: "#fff" } },
        error:   { iconTheme: { primary: "#DC2626",  secondary: "#fff" } },
      }} />
    </QueryClientProvider>
  );
}
