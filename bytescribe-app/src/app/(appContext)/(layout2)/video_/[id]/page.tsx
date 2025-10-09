"use client";
import React, { use } from "react";
import { Container } from "@mui/material";
import VideoPlayer from "@/components/VideoPlayer";

export default function VideoPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);

  return (
    <Container maxWidth="xl">
      <VideoPlayer id={id} />
    </Container>
  );
}
