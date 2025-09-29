"use client";
import { Box, Container } from "@mui/material";
import Image from "next/image";

export default function Layout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
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
  );
}
