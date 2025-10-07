"use client";
import { ArticleSummaryContext } from "@/contexts/ArticleSummary";
import {
  Backdrop,
  Box,
  BoxProps,
  Button,
  CircularProgress,
  LinearProgress,
  InputLabel,
  TextField,
  Typography,
  useTheme,
} from "@mui/material";
import { useRouter } from "next/navigation";
import { useContext, useEffect, useState } from "react";
import { Controller, useForm } from "react-hook-form";

export default function UrlBox(props: BoxProps) {
  const { control, handleSubmit } = useForm({
    defaultValues: {
      urlPath: "",
    },
    mode: "onChange",
  });

  const [loading, setLoading] = useState(false);
  // Async job UI state
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<string | null>(null);
  const [jobProgress, setJobProgress] = useState<string | null>(null);
  const [polling, setPolling] = useState(false);
  const router = useRouter();

  const { setSummary } = useContext(ArticleSummaryContext);

  const apiUrl = process.env.NEXT_PUBLIC_CRAWLER_API;
  const mediaUrl = process.env.NEXT_PUBLIC_S3_BUCKET;

  // checkJobStatus will be performed inside the polling effect to avoid
  // creating a changing dependency for the effect.

  const onSubmit = async (data: { urlPath: string }) => {
    const { urlPath } = data;
    if (!apiUrl) {
      alert("Lambda API URL not configured. Set NEXT_PUBLIC_CRAWLER_API.");
      return;
    }

    setLoading(true);
    setJobId(null);
    setJobStatus(null);

    const requestBody: Record<string, unknown> = {
      url: encodeURI(urlPath),
      full: true,
      async: true, // always use async per request
    };

    const getErrorMessage = (err: unknown) => {
      if (typeof err === "string") return err;
      if (err && typeof err === "object" && "message" in err)
        return String((err as { message?: unknown }).message ?? "");
      return String(err ?? "");
    };

    try {
      const res = await fetch(apiUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody),
      });
      if (!res.ok) {
        const t = await res.text();
        throw new Error(`HTTP ${res.status}: ${t}`);
      }
      const resp = await res.json();

      // If async mode, backend may return job_id
      if (resp && resp.job_id) {
        setJobId(resp.job_id);
        setJobStatus(
          (resp as Record<string, unknown>).status
            ? String((resp as Record<string, unknown>).status)
            : "processing",
        );
        setJobProgress(
          (resp as Record<string, unknown>).message
            ? String((resp as Record<string, unknown>).message)
            : null,
        );
        setPolling(true);
      } else {
        // if backend returned immediate result (unlikely in async flow), try to process it
        const hasSummary =
          resp &&
          typeof resp === "object" &&
          (resp as Record<string, unknown>).summary !== undefined;
        if (!hasSummary) {
          throw new Error(`No data returned for this article.`);
        }
        const respObj = resp as Record<string, unknown>;
        // safe extraction of bullets
        const bullets = Array.isArray(
          respObj.summary &&
            (respObj.summary as Record<string, unknown>).bullets,
        )
          ? ((respObj.summary as Record<string, unknown>).bullets as Array<
              Record<string, unknown>
            >)
          : [];
        const highlights: {
          text: string;
          image?: {
            url: string;
            s3_key: string;
            title: string;
            caption: string;
          };
        }[] = [];
        highlights.push({ text: String(respObj.title || "") });
        bullets.forEach((bullet) => {
          const text = bullet.text ? String(bullet.text) : "";
          const imageArr = Array.isArray(bullet.image_url)
            ? (bullet.image_url as Array<Record<string, unknown>>)
            : undefined;
          const firstImg = imageArr && imageArr[0] ? imageArr[0] : undefined;
          const image =
            firstImg && firstImg.image_url
              ? {
                  url: String(firstImg.image_url),
                  s3_key: String(firstImg.image_url).replace(
                    "s3://bytescribe-image-audio-bucket/",
                    "",
                  ),
                  title: String(firstImg.title ?? ""),
                  caption: String(firstImg.caption ?? ""),
                }
              : undefined;
          highlights.push({ text, image });
        });
        setSummary({ title: String(respObj.title || ""), highlights });
        router.push("adjust");
      }
    } catch (err: unknown) {
      console.error(err);
      alert(`Error sending URL: ${getErrorMessage(err)}`);
    } finally {
      setLoading(false);
    }
  };

  const { palette } = useTheme();

  // Polling effect for async jobs — keeps check logic local so the effect
  // dependencies don't change on every render.
  useEffect(() => {
    if (!polling || !jobId) return;
    let mounted = true;
    const fetchStatus = async (id: string) => {
      if (!apiUrl) return null;
      try {
        const res = await fetch(apiUrl, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action: "job_status", job_id: id }),
        });
        if (!res.ok) {
          const t = await res.text();
          throw new Error(`HTTP ${res.status}: ${t}`);
        }
        return await res.json();
      } catch (err) {
        console.error("Error checking job status", err);
        return null;
      }
    };

    const interval = setInterval(async () => {
      const status = await fetchStatus(String(jobId));
      if (!mounted || !status) return;
      setJobStatus(status.status || null);
      setJobProgress(
        (status.progress as string) || (status.message as string) || null,
      );
      if (status.status === "completed") {
        setPolling(false);
        setJobId(null);
        // job may include result under 'result' or 'summary' or full body
        const respObj = (status.result ?? status) as Record<string, unknown>;
        const bullets = Array.isArray(
          respObj.summary &&
            (respObj.summary as Record<string, unknown>).bullets,
        )
          ? ((respObj.summary as Record<string, unknown>).bullets as Array<
              Record<string, unknown>
            >)
          : [];
        if (bullets.length) {
          const highlights: {
            text: string;
            image?: {
              url: string;
              s3_key: string;
              title: string;
              caption: string;
            };
          }[] = [];
          highlights.push({ text: String(respObj.title || "") });
          bullets.forEach((bullet) => {
            const text = bullet.text ? String(bullet.text) : "";
            const imageArr = Array.isArray(bullet.image_url)
              ? (bullet.image_url as Array<Record<string, unknown>>)
              : undefined;
            const firstImg = imageArr && imageArr[0] ? imageArr[0] : undefined;
            const image =
              firstImg && firstImg.image_url
                ? {
                    url: String(firstImg.image_url),
                    s3_key: String(firstImg.image_url).replace(
                      "s3://bytescribe-image-audio-bucket/",
                      "",
                    ),
                    title: String(firstImg.title ?? ""),
                    caption: String(firstImg.caption ?? ""),
                  }
                : undefined;
            highlights.push({ text, image });
          });
          setSummary({ title: String(respObj.title || ""), highlights });
          router.push("adjust");
        } else if ((status as Record<string, unknown>).summary) {
          setSummary({
            title: String(
              (status as Record<string, unknown>).title || "Result",
            ),
            highlights: [],
          });
          router.push("adjust");
        } else {
          alert("Job completed but no result available.");
        }
      } else if (status.status === "failed") {
        setPolling(false);
        setJobId(null);
        alert((status as Record<string, unknown>).error || "Job failed");
      }
    }, 3000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, [polling, jobId, apiUrl, mediaUrl, router, setSummary]);

  return (
    <>
      <form onSubmit={handleSubmit(onSubmit)}>
        {(loading || polling) && <LinearProgress />}
        <Box
          display={"flex"}
          flexDirection={"column"}
          gap={2}
          justifyContent={"center"}
          {...props}
        >
          <Box
            display={"flex"}
            gap={2}
            justifyContent={"center"}
            alignItems={"center"}
          >
            <Box>
              <InputLabel htmlFor="input-url">URL: </InputLabel>
            </Box>

            <Controller
              name="urlPath"
              control={control}
              render={({ field, fieldState }) => (
                <>
                  <TextField
                    id="input-url"
                    label=""
                    variant="outlined"
                    fullWidth
                    {...field}
                    required
                    disabled={loading || polling}
                    error={!!fieldState.error}
                    helperText={
                      fieldState.error &&
                      (fieldState.error.message || "Failed to validate.")
                    }
                    sx={{ height: "3.5rem", boxShadow: 2, borderRadius: 1 }}
                  ></TextField>
                </>
              )}
              rules={{
                pattern: {
                  message: "Invalid url.",
                  value:
                    /[(http(s)?):\/\/(www\.)?a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,6}\b([-a-zA-Z0-9@:%_\+.~#?&//=]*)/,
                },
                required: "Please enter a valid url.",
              }}
            />
          </Box>
          <Button
            variant="contained"
            type="submit"
            disabled={loading || polling}
            sx={{ alignSelf: "end" }}
          >
            {loading || polling ? (
              <>
                <CircularProgress size={16} color="inherit" sx={{ mr: 1 }} />
                Crawling…
              </>
            ) : (
              "Go"
            )}
          </Button>
          {/* (async submission only) */}
        </Box>
      </form>
      {/* Job status panel for async mode */}
      {(polling || jobStatus) && (
        <Box mt={2} p={1} sx={{ border: "1px solid #ddd", borderRadius: 1 }}>
          <Typography variant="subtitle2">Job Status</Typography>
          <Box fontSize={13} mt={1}>
            <div>
              <strong>Job ID:</strong> {jobId || "(no active job)"}
            </div>
            <div>
              <strong>Status:</strong> {jobStatus || "-"}
            </div>
            {jobProgress && (
              <div style={{ marginTop: 6 }}>
                <strong>Progress:</strong> {jobProgress}
              </div>
            )}
            {polling && (
              <div style={{ marginTop: 8, fontSize: 12, color: "#666" }}>
                Polling for updates…
              </div>
            )}
          </Box>
        </Box>
      )}
      <Backdrop
        open={loading || polling}
        sx={palette.mode === "dark" ? { bgcolor: "rgba(0, 0, 0, 0.9)" } : {}}
      >
        <Box
          display={"flex"}
          flexDirection={"column"}
          gap={2}
          alignItems={"center"}
        >
          <Box display={"flex"} gap={2} alignItems={"center"}>
            <CircularProgress color="inherit" />
            <Typography variant="h6">
              {polling ? "Generating Highlights..." : "Reading your link..."}
            </Typography>
          </Box>
          {jobProgress && (
            <Typography variant="body2" sx={{ opacity: 0.9 }}>
              {jobProgress}
            </Typography>
          )}
        </Box>
      </Backdrop>
    </>
  );
}
