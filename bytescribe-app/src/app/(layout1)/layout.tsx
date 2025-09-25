"use client";
import { Box, Container } from "@mui/material";
import Image from "next/image";
import { useState } from "react";
import { ArticleSummaryContext } from "@/contexts/ArticleSummary";

export default function Layout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const [summary, setSummary] = useState({});

  return (
  <ArticleSummaryContext.Provider value={{summary, setSummary}}>
      <Container component={"main"}>
        <Box display={"flex"} justifyContent={"center"} py={3}>
          <Image
            src="/page2play.png"
            alt="Page2Play logo"
            width={128}
            height={121}
            priority
          />
        </Box>
        {children}
      </Container>
    </ArticleSummaryContext.Provider>
  );
}
