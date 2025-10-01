"use client";
import { useState } from "react";
import { ArticleSummaryContext } from "@/contexts/ArticleSummary";

export default function AppContext({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const [summary, setSummary] = useState({});

  return (
    <ArticleSummaryContext.Provider value={{ summary, setSummary }}>
      {children}
    </ArticleSummaryContext.Provider>
  );
}
