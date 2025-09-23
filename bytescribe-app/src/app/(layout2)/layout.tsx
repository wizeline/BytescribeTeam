import { Metadata } from "next";
import { Box, Container } from "@mui/material";
import Image from "next/image";

export const metadata: Metadata = {
  title: "Page2Play",
  description: "AI-powered content generation platform",
};

export default function Layout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <Container component={"main"}>
      <Box display={"flex"} py={2}>
        <Image
          src="/page2play.png"
          alt="Page2Play logo"
          width={96}
          height={91}
          priority
        />
      </Box>
      {children}
    </Container>
  );
}
