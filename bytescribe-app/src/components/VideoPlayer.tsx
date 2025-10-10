"use client";
import React, { useCallback, useEffect, useMemo, useState } from "react";
import ReactPlayer from "react-player";
import {
  Box,
  Backdrop,
  Button,
  LinearProgress,
  Typography,
} from "@mui/material";
import { useRouter } from "next/navigation";

const mediaUrl = process.env.NEXT_PUBLIC_S3_BUCKET || "";
const VIDEO_TIMEOUT = 300000;
const INTERVAL_DELAY = 10000;
const ratioOptions = ["16:9", "9:16", "1:1"];

export default function VideoPlayer({
  id,
  initRatio,
  onLoaded,
}: {
  id: string;
  initRatio?: string;
  onLoaded?: (available: boolean) => void;
}) {
  const videoUrl = `${mediaUrl}/output_videos/${id}.mp4`;
  const [ratio, setRatio] = useState(
    ratioOptions.includes(initRatio || "") ? initRatio : "16:9",
  );
  const [vWidth, vHeight] = useMemo(() => {
    switch (ratio) {
      case "1:1":
        return [480, 480];
      case "9:16":
        return [360, 640];
      default:
        return [640, 360];
    }
  }, [ratio]);

  useEffect(() => {
    if (ratioOptions.includes(initRatio || "")) {
      setRatio(initRatio!);
    }
  }, [initRatio]);

  const [available, setAvailable] = useState(false);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(1);

  useEffect(() => {
    if (!!id) {
      setAvailable(false);
    }
  }, [id]);

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
    setProgress(1);

    const start = Date.now();
    const doesVideoExist = await checkAvailability();
    if (doesVideoExist) {
      setAvailable(true);
      setLoading(false);
    } else {
      let noOfAttempts = 1;

      const intervalId = setInterval(
        async () => {
          // Check if timeout reached
          const progress = Date.now() - start;
          if (progress >= VIDEO_TIMEOUT) {
            console.error("Timeout fetching video.");
            clearInterval(intervalId);
            setLoading(false);
            return;
          }

          noOfAttempts++;
          setProgress(
            progress > VIDEO_TIMEOUT / 2
              ? 99
              : (200 * progress) / VIDEO_TIMEOUT,
          );
          const availability = await checkAvailability();
          if (availability) {
            clearInterval(intervalId);
            setProgress(100);
            setAvailable(true);
            setLoading(false);
          }
        },
        noOfAttempts < 6 ? INTERVAL_DELAY : INTERVAL_DELAY * 3,
      );
    }
  }, [checkAvailability]);

  useEffect(() => {
    if (!!id && !available) {
      loadVideo();
    }
  }, [available, id, loadVideo]);

  const [renderTrigger, setRenderTrigger] = useState(0);
  useEffect(() => {
    if (available) {
      setRenderTrigger(renderTrigger + 1);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [available]);

  // Notify parent when loading finishes (either video available or loading stopped)
  useEffect(() => {
    if (!loading && onLoaded) {
      onLoaded(available);
    }
    // We intentionally only listen to loading and available changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loading, available]);

  const router = useRouter();

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
          {!!id && !available && !loading && (
            <Typography>
              This takes longer than expected. Try reload later.
            </Typography>
          )}
          <Box position={"relative"}>
            <ReactPlayer
              key={renderTrigger}
              src={videoUrl}
              controls={true}
              volume={0.25}
              width={vWidth}
              height={vHeight}
            />
            <Backdrop
              open={loading}
              sx={{ zIndex: (theme) => theme.zIndex.drawer + 2, color: "#fff" }}
            >
              <Box sx={{ width: "80%", maxWidth: 800, textAlign: "center" }}>
                <LinearProgress variant="determinate" value={progress} />
                <Box display="flex" justifyContent="center" sx={{ py: 1 }}>
                  <Typography variant="body2">
                    Rendering video... {Math.round(progress)}%
                  </Typography>
                </Box>
              </Box>
            </Backdrop>
          </Box>
        </Box>
        <Box
          display={"flex"}
          justifyContent={"space-between"}
          alignItems={"center"}
        >
          <Box display={"flex"} gap={2} flex={1} justifyContent={"flex-start"}>
            <Button variant="contained" onClick={() => router.push("/adjust")}>
              Go Back
            </Button>
          </Box>

          <Box display={"flex"} gap={2} flex={1} justifyContent={"center"}>
            {available ? (
              <Button
                variant="contained"
                onClick={() => {
                  window.open(videoUrl, "_blank");
                }}
              >
                Download
              </Button>
            ) : (
              !!id &&
              !loading && (
                <Button
                  variant="contained"
                  disabled={loading}
                  onClick={loadVideo}
                >
                  Reload
                </Button>
              )
            )}
          </Box>

          <Box display={"flex"} gap={2} flex={1} justifyContent={"flex-end"}>
            <Button variant="outlined" onClick={() => router.push("/home")}>
              Go Home
            </Button>
          </Box>
        </Box>
      </Box>
    </>
  );
}
