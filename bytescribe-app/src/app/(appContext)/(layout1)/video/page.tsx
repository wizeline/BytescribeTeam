"use client";
import React, { useCallback, useContext, useEffect, useState } from "react";
import {
  Box,
  Button,
  CircularProgress,
  Container,
  InputLabel,
  MenuItem,
  Slider,
  TextField,
} from "@mui/material";
import VideoPlayer from "@/components/VideoPlayer";
import { Controller, useForm } from "react-hook-form";
import { ArticleSummaryContext } from "@/contexts/ArticleSummary";
import { redirect } from "next/navigation";

const apiUrl = process.env.NEXT_PUBLIC_ELEVENLABS_API;

enum VOICES {
  Daniel = "onwK4e9ZLuTAKqWW03F9",
  George = "JBFqnCBsd6RMkjVDRZzb",
  Liam = "TX3LPaxmHKxFdv7VOQHJ",
  Matilda = "XrExE9yKIg1WjnnlVkGX",
  Sarah = "EXAVITQu4vr4xnSDxMaL",
}

enum RATIO {
  "16:9" = "1920x1080 - Default",
  "9:16" = "Vertical for mobile/shorts",
  "1:1" = "Square for social media",
}

const TRANSITIONS = ["fade", "cut", "slide"];

const JOB_TIMEOUT = 300000;
const INTERVAL_DELAY = 10000;

export default function VideoPage() {
  const {
    summary: { title, highlights },
  } = useContext(ArticleSummaryContext);
  if (!title || !highlights?.length) {
    redirect("/home");
  }

  const [videoId, setVideoId] = useState("");
  const [videoRatio, setVideoRatio] = useState("16:9");

  const initForm = {
    voiceId: VOICES.Daniel,
    ratio: "16:9",
    transition: TRANSITIONS[0],
    wordChunk: 3,
  };
  const { control, handleSubmit } = useForm({
    defaultValues: initForm,
  });

  const [savedConfig, setSavedConfig] = useState<typeof initForm>();

  const [jobId, setJobId] = useState("");
  const [jobStatus, setJobStatus] = useState("");
  const [loading, setLoading] = useState(false);

  const fetchJob = useCallback(async () => {
    const payload = {
      action: "job_status",
      job_id: jobId,
    };

    let result;

    if (!apiUrl) {
      alert("Lambda API URL not configured. Set NEXT_PUBLIC_ELEVENLABS_API.");
      return;
    }

    await fetch(apiUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`Request failed with ${response.status}`);
        }

        const data: { body: { status: string } } = await response.json();
        result = data.body;
      })
      .catch((err) => {
        console.error(err);
        result = {
          status: "error",
          message: `Error fetch job ${jobId}: ${err.message || err}`,
        };
      });

    return result;
  }, [jobId]);

  const fetchHighlights = useCallback(async () => {
    setLoading(true);

    const start = Date.now();
    const intervalId = setInterval(async () => {
      // Check if timeout reached
      if (Date.now() - start >= JOB_TIMEOUT) {
        console.error("Timeout.");
        clearInterval(intervalId);
        setJobStatus("timeout");
        setLoading(false);
        alert("Recording session is taking too long. We're so sorry for this.");
        return;
      }

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const job: any = await fetchJob();

      if (job?.status === "completed") {
        setJobStatus("completed");
        setLoading(false);
        clearInterval(intervalId);
      }
    }, INTERVAL_DELAY);
  }, [fetchJob]);

  useEffect(() => {
    if (!!jobId) {
      if (jobStatus === "completed") {
        setVideoId(jobId);
        setVideoRatio(savedConfig!.ratio);
      } else {
        fetchHighlights();
      }
    }
  }, [fetchHighlights, jobId, jobStatus, savedConfig]);

  const onSubmit = (formData: typeof initForm) => {
    if (!apiUrl) {
      alert("Lambda API URL not configured. Set NEXT_PUBLIC_ELEVENLABS_API.");
      return;
    }

    setLoading(true);

    const payload = {
      ...formData,
      async: true, // Always true
      highlights: [
        { text: title! },
        ...highlights!.filter(({ text }) => text !== title),
      ],
    };

    fetch(apiUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`Request failed with ${response.status}`);
        }

        const data = await response.json();
        const jobId = data.body?.job_id;
        if (!jobId) {
          throw new Error(`No job id return.`);
        }

        setJobId(jobId);
        setJobStatus("processing");
        setSavedConfig(formData);
      })
      .catch((err) => {
        console.error(err);
        alert("Oops! Seem like all the staffs are busy. Try again later.");
        setLoading(false);
      });
  };

  return (
    <Container maxWidth="xl">
      <form
        onSubmit={handleSubmit(onSubmit)}
        style={{
          display: "flex",
          flexDirection: "column",
          marginBottom: "4rem",
        }}
      >
        <Box
          display={"flex"}
          flexDirection={"row"}
          justifyContent={"space-between"}
          mb={2}
          sx={{ "& .MuiTextField-root": { width: "40%" } }}
        >
          <Controller
            name="voiceId"
            control={control}
            render={({ field, fieldState }) => (
              <>
                <TextField
                  id="voice-select"
                  label="Narrator:"
                  select
                  {...field}
                  required
                  disabled={loading}
                  error={!!fieldState.error}
                  helperText={
                    fieldState.error &&
                    (fieldState.error.message || "Failed to validate.")
                  }
                  size="small"
                >
                  {Object.keys(VOICES).map((value) => (
                    <MenuItem
                      key={value}
                      value={VOICES[value as keyof typeof VOICES]}
                    >
                      {value}
                    </MenuItem>
                  ))}
                </TextField>
              </>
            )}
            rules={{
              required: "Please select a narrator.",
            }}
          />

          <Controller
            name="ratio"
            control={control}
            render={({ field, fieldState }) => (
              <>
                <TextField
                  id="ratio-select"
                  label="Aspect Ratio:"
                  select
                  {...field}
                  required
                  disabled={loading}
                  error={!!fieldState.error}
                  helperText={
                    fieldState.error &&
                    (fieldState.error.message || "Failed to validate.")
                  }
                  size="small"
                >
                  {Object.keys(RATIO).map((value) => (
                    <MenuItem key={value} value={value}>
                      {RATIO[value as keyof typeof RATIO]}
                    </MenuItem>
                  ))}
                </TextField>
              </>
            )}
            rules={{
              required: "Please select a ratio.",
            }}
          />
        </Box>

        <Box
          display={"flex"}
          flexDirection={"row"}
          justifyContent={"space-between"}
          mb={2}
          sx={{ "& .MuiFormControl-root": { width: "40%" } }}
        >
          <Controller
            name="transition"
            control={control}
            render={({ field, fieldState }) => (
              <>
                <TextField
                  id="transition-select"
                  select
                  label="Transition Effect:"
                  {...field}
                  required
                  disabled={loading}
                  error={!!fieldState.error}
                  helperText={
                    fieldState.error &&
                    (fieldState.error.message || "Failed to validate.")
                  }
                  size="small"
                >
                  {TRANSITIONS.map((style) => (
                    <MenuItem
                      key={style}
                      value={style}
                      sx={{ textTransform: "capitalize" }}
                    >
                      {style}
                    </MenuItem>
                  ))}
                </TextField>
              </>
            )}
            rules={{
              required: "Please select a transition style.",
            }}
          />

          <Controller
            name="wordChunk"
            control={control}
            render={({ field }) => (
              <Box width={"40%"}>
                <InputLabel>
                  Subtitle chunk size: <b>{field.value}</b>
                </InputLabel>
                <Box>
                  <Slider
                    value={field.value}
                    valueLabelDisplay="off"
                    shiftStep={1}
                    step={1}
                    marks
                    min={3}
                    max={6}
                    onChange={field.onChange}
                    disabled={loading}
                  />
                </Box>
              </Box>
            )}
            rules={{
              required: "Please select a size.",
            }}
          />
        </Box>

        <Button
          variant="contained"
          type="submit"
          disabled={loading}
          sx={{ alignSelf: "end" }}
        >
          {loading ? (
            <>
              <CircularProgress size={16} color="inherit" sx={{ mr: 1 }} />
              Generating…
            </>
          ) : (
            "Generate"
          )}
        </Button>
      </form>

      <VideoPlayer id={videoId} initRatio={videoRatio} />
    </Container>
  );
}
