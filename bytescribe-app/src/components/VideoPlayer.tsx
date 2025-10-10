"use client";
import React, { useCallback, useEffect, useMemo, useState } from "react";
import ReactPlayer from "react-player";
import {
  Backdrop,
  Box,
  Button,
  CircularProgress,
  Typography,
  useTheme,
} from "@mui/material";
import { useRouter } from "next/navigation";

const VIDEO_TIMEOUT = 300000;
const INTERVAL_DELAY = 10000;
const availableRatios = ["16:9", "9:16", "1:1"];

export default function VideoPlayer({ id, initRatio }: { id: string, initRatio?: string }) {
  const mediaUrl = process.env.NEXT_PUBLIC_S3_BUCKET || "";
  const videoUrl = `${mediaUrl}/output_videos/${id}.mp4`;

  const [ratio, setRatio] = useState(availableRatios.includes(initRatio || "") ? initRatio : "16:9");
  const videoWidth = useMemo(() => ratio === "9:16" ? 360 : 640, [ratio]);
  const videoHeight = useMemo(() => ratio === "16:9" ? 360 : 640, [ratio]);

  useEffect(() => {
    if (availableRatios.includes(initRatio || "")) {
      setRatio(initRatio!);
    }}, [initRatio])

  const [available, setAvailable] = useState(false);
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const checkAvailability = useCallback(async () => {
    try {
      const response = await fetch(videoUrl, { method: "HEAD" });
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
  }, [videoUrl]);

  const loadVideo = useCallback(async () => {
    setLoading(true);

    const doesVideoExist = await checkAvailability();
    if (doesVideoExist) {
      setAvailable(true);
      setLoading(false);
    } else {
      let noOfAttempts = 1;

      const start = Date.now();
      const intervalId = setInterval(
        async () => {
          // Check if timeout reached
          if (Date.now() - start >= VIDEO_TIMEOUT) {
            console.log("Sorry, timeout.");
            clearInterval(intervalId);
            setLoading(false);
            return;
          }

          noOfAttempts++;
          const availability = await checkAvailability();
          if (availability) {
            clearInterval(intervalId);
            setAvailable(true);
            setLoading(false);
          }
        },
        noOfAttempts < 6 ? INTERVAL_DELAY : INTERVAL_DELAY * 3,
      );
    }
  }, [checkAvailability]);

  useEffect(() => {
    if (!!id && id !== "not_found" && !available) {
      loadVideo();
    }
  }, [available, id, loadVideo]);

  const { palette } = useTheme();

  return (
    <>
      <Box display={"flex"} flexDirection={"column"} gap={4} marginBottom={5}>
        <Box
          display={"flex"}
          flexDirection={"column"}
          justifyContent={"center"}
          alignItems={"center"}
          gap={2}
        >
          {!available && !loading && (
            <Typography variant="h5">
              This takes longer than expected. Try reload later.
            </Typography>
          )}
          <ReactPlayer
            key={available ? "O" : "I"}
            src={videoUrl}
            controls={true}
            volume={0.25}
            width={videoWidth}
            height={videoHeight}
          />
        </Box>
        <Box
          display={"flex"}
          justifyContent={"space-between"}
          alignItems={"center"}
        >
          <Box display={"flex"} gap={2}>
            <Button variant="contained" onClick={() => router.push("/adjust")}>
              Go Back
            </Button>
          </Box>
          <Box display={"flex"} gap={2}>
            {available ?  (
              <Button
                variant="contained"
                onClick={() => {
                  window.open(videoUrl, '_blank');
                }}
              >
                Download
              </Button>
            ) : (
              <Button
                variant="contained"
                disabled={loading}
                onClick={loadVideo}
              >
                Reload
              </Button>
            )}
            <Button variant="outlined" onClick={() => router.push("/home")}>
              Go Home
            </Button>
          </Box>
        </Box>
      </Box>
      <Backdrop
        open={loading}
        sx={palette.mode === "dark" ? { bgcolor: "rgba(0, 0, 0, 0.9)" } : {}}
      >
        <Box display={"flex"} gap={2} alignItems={"center"}>
          <CircularProgress color="inherit" />
          <Typography variant="h6">Rendering video...</Typography>
        </Box>
      </Backdrop>
    </>
  );
}
