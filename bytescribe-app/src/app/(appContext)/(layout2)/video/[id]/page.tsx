"use client";
import React, { use, useCallback, useEffect, useState } from "react";
import ReactPlayer from "react-player";
import {
  Backdrop,
  Box,
  Button,
  CircularProgress,
  Container,
  Typography,
} from "@mui/material";
import { useRouter } from "next/navigation";

export default function VideoPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const objectUrl = `https://bytescribe-image-audio-bucket.s3.ap-southeast-2.amazonaws.com/output_videos/${id}.mp4`;

  const [available, setAvailable] = useState(false);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  const checkAvailability = useCallback(async () => {
    try {
      const response = await fetch(objectUrl, { method: "HEAD" });
      if (response.ok) {
        console.log("Video found!");
        return true;
      } else {
        console.log("Video is not available.");
        return false;
      }
    } catch (error) {
      console.log("Error checking video:", error);
      return false;
    }
  }, [objectUrl]);

  useEffect(() => {
    if (!!id && id !== "not_found" && !available) {
      (async () => {
        const doesVideoExist = await checkAvailability();
        if (doesVideoExist) {
          setAvailable(true);
          setLoading(false);
        } else {
          const start = Date.now();
          const intervalId = setInterval(async () => {
            // Check if timeout reached
            if (Date.now() - start >= 30000) {
              console.log("Sorry, timeout.");
              clearInterval(intervalId);
              setLoading(false);
              return;
            }

            const availability = await checkAvailability();
            if (availability) {
              clearInterval(intervalId);
              setAvailable(true);
              setLoading(false);
            }
          }, 5000);
        }
      })();
    }
  }, [checkAvailability, id, objectUrl, available]);

  return (
    <Container maxWidth="xl">
      <Box display={"flex"} flexDirection={"column"} gap={2} marginBottom={5}>
        <Box
          display={"flex"}
          flexDirection={"column"}
          justifyContent={"center"}
          alignItems={"center"}
          gap={2}
        >
          {!available && !loading && (
            <Typography variant="h5">
              Sorry, video is not available right now.
            </Typography>
          )}
          <ReactPlayer
            key={available ? "O" : "I"}
            src={objectUrl}
            controls={true}
            volume={0.25}
            width={640}
            height={360}
          />
        </Box>
        <Button
          variant="contained"
          sx={{ alignSelf: "end" }}
          onClick={() => router.push("/adjust")}
        >
          Go Back
        </Button>
      </Box>
      <Backdrop open={loading}>
        <CircularProgress color="inherit" />
      </Backdrop>
    </Container>
  );
}
