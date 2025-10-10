"use client";

import Image from "next/image";
import { DataGrid, GridColDef } from "@mui/x-data-grid";
import { useFieldArray, useForm } from "react-hook-form";
import {
  Box,
  Button,
  Backdrop,
  LinearProgress,
  FormHelperText,
  MenuItem,
  Paper,
  Tooltip,
  Select,
  Typography,
  TextField,
  Slider,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Skeleton,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import * as yup from "yup";
import { yupResolver } from "@hookform/resolvers/yup";
import { useContext, useEffect, useMemo, useState } from "react";
import { ArticleSummaryContext } from "@/contexts/ArticleSummary";
import { useRouter } from "next/navigation";

const schema = yup
  .object({
    items: yup
      .array()
      .of(
        yup
          .object({
            order: yup.number().required("ID must be required"),
            text: yup
              .string()
              .max(512, "Highlight text can't be longer than 512 characters")
              .required("Highlights is required"),
            image: yup.string().required().nullable(),
            // imageCaption: yup.string(),
          })
          .required(),
      )
      .required(),
  })
  .required();

const placeHolderImg = "/wizeline1-640x400.jpg";

const availableModelOptions = [
  {
    value: "anthropic.claude-3-haiku-20240307-v1:0",
    label: "Anthropic Claude 3 Haiku",
  },
  {
    value: "anthropic.claude-3-sonnet-20240229-v1:0",
    label: "Anthropic Claude 3 Sonnet",
  },
  {
    value: "anthropic.claude-3-5-sonnet-20240620-v1:0",
    label: "Anthropic Claude 3.5 Sonnet",
  },
];

const availableToneOptions = [
  { value: "formal", label: "Formal" },
  { value: "casual", label: "Casual" },
  { value: "technical", label: "Technical" },
  { value: "marketing", label: "Marketing" },
  { value: "humorous", label: "Humorous" },
];

export default function HighlightsTable() {
  const { summary, setSummary } = useContext(ArticleSummaryContext);
  const { highlights } = summary;

  // Prevent rendering until after client hydration to avoid
  // server/client markup mismatches when this component depends
  // on client-only context or environment values.
  const [isMounted, setIsMounted] = useState(false);
  useEffect(() => {
    setIsMounted(true);
  }, []);

  // Accordion states for collapsing sections
  const [configExpanded, setConfigExpanded] = useState(true);
  const [highlightsExpanded, setHighlightsExpanded] = useState(true);

  const normalizeImageUrl = (url?: string | null) => {
    if (!url) return null;
    // Already an http(s) url
    if (url.startsWith("http://") || url.startsWith("https://")) return url;
    // s3://bucket/key -> try to convert
    if (url.startsWith("s3://")) {
      const configured = process.env.NEXT_PUBLIC_S3_BUCKET?.replace(/\/$/, "");
      // common internal replacement used elsewhere in repo
      const prefix = "s3://bytescribe-image-audio-bucket/";
      if (configured && url.startsWith(prefix)) {
        return configured + "/" + url.slice(prefix.length);
      }
      // generic fallback: s3://bucket/key -> https://bucket.s3.amazonaws.com/key
      const without = url.slice(5); // remove s3://
      const idx = without.indexOf("/");
      if (idx === -1) return `https://${without}.s3.amazonaws.com`;
      const bucket = without.slice(0, idx);
      const key = without.slice(idx + 1);
      return `https://${bucket}.s3.amazonaws.com/${key}`;
    }
    return url;
  };

  // Maintain a persistent list of available images that merges new images from
  // `highlights` but does not remove previously-seen images. This prevents a
  // scenario where changing one row's image removes that image from the
  // selection list for other rows.
  const [availableImages, setAvailableImages] = useState(() => {
    const initial = (highlights || [])
      .map(({ image }) =>
        image
          ? {
            url: normalizeImageUrl(image.url) || "",
            title: String(image.title ?? ""),
            caption: String(image.caption ?? ""),
            s3_key: image.s3_key ?? "",
          }
          : null,
      )
      .filter(Boolean) as {
        url: string;
        caption: string;
        title: string;
        s3_key: string;
      }[];
    // dedupe by url preserving first occurrence
    const map = new Map<string, (typeof initial)[0]>();
    initial.forEach((img) => map.set(img.url, img));
    return Array.from(map.values());
  });

  // Merge new images from highlights whenever highlights change, but keep any
  // previously seen images in `availableImages`.
  useEffect(() => {
    const newImgs = (highlights || [])
      .map(({ image }) =>
        image
          ? {
            url: normalizeImageUrl(image.url) || "",
            title: String(image.title ?? ""),
            caption: String(image.caption ?? ""),
            s3_key: image.s3_key ?? "",
          }
          : null,
      )
      .filter(Boolean) as {
        url: string;
        caption: string;
        title: string;
        s3_key: string;
      }[];

    if (newImgs.length === 0) return;
    setAvailableImages((prev) => {
      const map = new Map<string, (typeof newImgs)[0]>();
      prev.forEach((p) => map.set(p.url, p));
      newImgs.forEach((n) => map.set(n.url, n));
      return Array.from(map.values());
    });
  }, [highlights]);

  // The first item in `highlights` is the page title (index 0).
  // Keep DataGrid rows to only the actual highlights (index > 0),
  // but preserve the original `order` index so updates map back correctly.
  const [rowData, setRowData] = useState(
    (highlights || [])
      .map(({ text, image }, id) =>
        id === 0
          ? null
          : {
            order: id,
            text: text,
            image: normalizeImageUrl(image?.url) || null,
            imageCaption: String(image?.caption ?? ""),
          },
      )
      .filter((r) => !!r) as {
        order: number;
        text: string;
        image: string | null;
        imageCaption: string;
      }[],
  );

  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  // UI controls for generating highlights
  // Default to the 3.5 Sonnet model so it's selected by default
  const [modelId, setModelId] = useState(
    "anthropic.claude-3-5-sonnet-20240620-v1:0",
  );
  // Tone selection for generated summary
  const [summaryTone, setSummaryTone] = useState<string>("formal");
  const [temperatureValue, setTemperatureValue] = useState<number>(0.2);
  const [wordsPerHighlight, setWordsPerHighlight] = useState<number>(60);
  const [numHighlights, setNumHighlights] = useState<number>(3);

  const {
    control,
    handleSubmit,
    trigger,
    formState: { errors },
  } = useForm({
    defaultValues: {
      items: rowData.map(({ order, text, image }) => ({ order, text, image })),
    },
    resolver: yupResolver(schema),
  });

  const { fields, update } = useFieldArray({
    control: control,
    name: "items",
  });

  const updateRow = (newRowValue: (typeof rowData)[0]) => {
    const rowIndex = rowData.findIndex(
      (row) => newRowValue.order === row.order,
    );
    const newRows = [...rowData];
    newRows[rowIndex] = newRowValue;
    setRowData(newRows);

    const newHighlights = structuredClone(highlights!);
    const updateHighlightImage = newRowValue.image
      ? availableImages.find(({ url }) => newRowValue.image === url)
      : undefined;
    const updateHighlight = updateHighlightImage
      ? { text: newRowValue.text, image: updateHighlightImage }
      : { text: newRowValue.text };
    newHighlights[newRowValue.order] = updateHighlight;
    setSummary({
      ...summary,
      highlights: newHighlights,
    });

    const fieldIndex = fields.findIndex(
      (field) => newRowValue.order === field.order,
    );
    update(fieldIndex, newRowValue);
    trigger();
  };

  const columns: GridColDef<(typeof rowData)[number]>[] = useMemo(
    () => [
      {
        field: "order",
        headerName: "",
        align: "right",
        width: 60,
        renderCell({ value }) {
          return value || "Title";
        },
      },
      {
        field: "text",
        headerName: "Highlights",
        flex: 1,
        editable: true,
        renderCell: ({ value, row }) => {
          const index = fields.findIndex((field) => row.order === field.order);
          return (
            <Box position={"relative"} height={"100%"}>
              {value}
              {errors.items && errors.items[index]?.text && (
                <FormHelperText
                  error
                  sx={{ position: "absolute", bottom: "-1rem" }}
                >
                  {errors.items[index]?.text.message || "Field is error"}
                </FormHelperText>
              )}
            </Box>
          );
        },
      },
      {
        field: "image",
        headerName: "Images",
        width: 150,
        editable: true,
        renderCell: ({ value, row }) => (
          <Image
            src={value || placeHolderImg}
            alt={row.imageCaption || ""}
            width={120}
            height={80}
            priority
          />
        ),
        renderEditCell: ({ id, value, api, field }) => {
          // Show all images as clickable thumbnails inside the edit cell.
          // Clicking a thumbnail immediately sets the cell value and commits the change.
          return (
            <Box
              sx={{
                display: "flex",
                flexDirection: "column",
                gap: 1,
                alignItems: "flex-start",
                overflowY: "auto",
                maxHeight: 300,
                px: 1,
                py: 0.5,
                width: "100%",
              }}
            >
              {availableImages.map(
                (
                  { url, caption }: { url: string; caption: string },
                  idx: number,
                ) => {
                  const selected = url === value;
                  return (
                    <Box
                      key={`${url}-${idx}`}
                      onClick={() => {
                        // Update the cell value and stop edit mode so the change is committed
                        const apiWithEdit = api as unknown as {
                          stopCellEditMode?: (params: {
                            id: unknown;
                            field: string;
                          }) => void;
                          setCellMode?: (
                            id: unknown,
                            field: string,
                            mode: string,
                          ) => void;
                        };
                        try {
                          api.setEditCellValue({ id, field, value: url });
                          if (
                            typeof apiWithEdit.stopCellEditMode === "function"
                          ) {
                            apiWithEdit.stopCellEditMode({ id, field });
                          }
                        } catch {
                          if (typeof apiWithEdit.setCellMode === "function")
                            apiWithEdit.setCellMode(id, field, "view");
                        }
                      }}
                      sx={{
                        position: "relative",
                        cursor: "pointer",
                        borderRadius: 1,
                        border: (theme) =>
                          selected
                            ? `2px solid ${theme.palette.primary.main}`
                            : "2px solid transparent",
                        boxShadow: selected ? 2 : 0,
                        width: "100%",
                        display: "flex",
                        alignItems: "center",
                        gap: 1,
                        px: 1,
                        py: 0.5,
                        backgroundColor: (theme) =>
                          selected
                            ? theme.palette.action.selected
                            : "transparent",
                      }}
                    >
                      <Tooltip title={caption || ""} arrow>
                        <Box sx={{ display: "flex", alignItems: "center" }}>
                          <Image
                            src={url}
                            alt={caption || "image"}
                            width={120}
                            height={80}
                            priority
                          />
                        </Box>
                      </Tooltip>
                      {selected && (
                        <Box
                          sx={{
                            position: "absolute",
                            top: 6,
                            right: 6,
                            backgroundColor: "rgba(0,0,0,0.5)",
                            borderRadius: "50%",
                            width: 28,
                            height: 28,
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                          }}
                        >
                          <svg
                            xmlns="http://www.w3.org/2000/svg"
                            width="18"
                            height="18"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="white"
                            strokeWidth="2"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          >
                            <polyline points="20 6 9 17 4 12" />
                          </svg>
                        </Box>
                      )}
                    </Box>
                  );
                },
              )}
            </Box>
          );
        },
      },
    ],
    [errors.items, fields, availableImages],
  );

  // Animate a dummy determinate progress while loading to give feedback.
  // Aim: reach ~90% over ~5 seconds, updating every 200ms with small jitter.
  useEffect(() => {
    let timer: NodeJS.Timeout | null = null;
    if (loading) {
      // start at 0 now (slower ramp)
      setProgress(0);
      const intervalMs = 2000;
      const totalMs = 30000; // target ~30s to reach 90%
      const steps = Math.max(1, Math.round(totalMs / intervalMs));
      const perStep = 90 / steps; // from 0 -> 90
      timer = setInterval(() => {
        setProgress((p) => {
          if (p >= 90) return 90;
          const jitter = (Math.random() - 0.5) * Math.min(1, perStep * 0.25);
          const next = p + perStep + jitter;
          return Math.min(next, 90);
        });
      }, intervalMs);
    } else {
      // finish animation quickly when loading completes
      setProgress(100);
      const t = setTimeout(() => setProgress(0), 400);
      if (timer) clearInterval(timer);
      return () => clearTimeout(t);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [loading]);

  // Generate highlights action — calls crawler Lambda to get highlights from the stored URL
  const generateHighlights = async () => {
    const crawlerApiUrl = process.env.NEXT_PUBLIC_CRAWLER_API;

    if (!crawlerApiUrl) {
      alert("Crawler API URL not configured. Set NEXT_PUBLIC_CRAWLER_API.");
      return;
    }

    if (!summary.url) {
      alert("No URL found. Please go back and enter a URL first.");
      return;
    }

    setLoading(true);
    try {
      const payload: Record<string, unknown> = {
        url: summary.url,
        full: true,
        async: true, // Use async mode for better UX
      };

      // Add Bedrock parameters if available
      if (modelId) payload.model_id = modelId;
      payload.text_config = {
        temperature: Number(temperatureValue),
        tone: summaryTone,
        maxTokenCount: 2048, // Default token count
        max_words_per_bullet: Number(wordsPerHighlight) || 60,
        num_bullets: Number(numHighlights) || 3,
      };

      const res = await fetch(crawlerApiUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const t = await res.text();
        throw new Error(`HTTP ${res.status}: ${t}`);
      }

      const data = await res.json();

      // Handle async response with job_id
      if (data && data.job_id) {
        // Start polling for job completion
        const jobId = data.job_id;
        const pollInterval = setInterval(async () => {
          try {
            const statusRes = await fetch(crawlerApiUrl, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ action: "job_status", job_id: jobId }),
            });

            if (statusRes.ok) {
              const statusData = await statusRes.json();

              if (statusData.status === "completed") {
                clearInterval(pollInterval);

                // Extract highlights from completed job
                const respObj = (statusData.result ?? statusData) as Record<
                  string,
                  unknown
                >;
                const bullets = Array.isArray(
                  respObj.summary &&
                  (respObj.summary as Record<string, unknown>).bullets,
                )
                  ? ((respObj.summary as Record<string, unknown>)
                    .bullets as Array<Record<string, unknown>>)
                  : [];

                if (bullets.length) {
                  const newHighlights: {
                    text: string;
                    image?: {
                      url: string;
                      s3_key: string;
                      title: string;
                      caption: string;
                    };
                  }[] = [];

                  // Add title as first highlight
                  newHighlights.push({ text: String(respObj.title || "") });

                  // Process bullets into highlights
                  bullets.forEach((bullet) => {
                    const text = bullet.text ? String(bullet.text) : "";
                    const imageArr = Array.isArray(bullet.image_url)
                      ? (bullet.image_url as Array<Record<string, unknown>>)
                      : undefined;
                    const firstImg =
                      imageArr && imageArr[0] ? imageArr[0] : undefined;
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
                    newHighlights.push({ text, image });
                  });

                  // Update summary and table data
                  setSummary({
                    ...summary,
                    title: String(respObj.title || ""),
                    highlights: newHighlights,
                  });

                  // Keep title (index 0) out of the DataGrid rows but preserve
                  // the original ordering index so edits map back into `highlights`.
                  const mapped = newHighlights
                    .map((h, id) => ({
                      order: id,
                      text: h.text,
                      image: normalizeImageUrl(h.image?.url) || null,
                      imageCaption: String(h.image?.caption ?? ""),
                    }))
                    .filter((r) => r.order > 0);
                  setRowData(mapped);
                  // Expand highlights and collapse configuration panel
                  setHighlightsExpanded(true);
                  setConfigExpanded(false);
                } else {
                  alert("No highlights found in the crawled content.");
                }
                setLoading(false);
              } else if (statusData.status === "failed") {
                clearInterval(pollInterval);
                setLoading(false);
                alert(
                  "Crawling job failed: " +
                  (statusData.error || "Unknown error"),
                );
              }
            }
          } catch (pollErr) {
            console.error("Error polling job status:", pollErr);
          }
        }, 3000); // Poll every 3 seconds
      } else {
        // Handle immediate response (non-async mode)
        const respObj = data as Record<string, unknown>;
        const bullets = Array.isArray(
          respObj.summary &&
          (respObj.summary as Record<string, unknown>).bullets,
        )
          ? ((respObj.summary as Record<string, unknown>).bullets as Array<
            Record<string, unknown>
          >)
          : [];

        if (bullets.length) {
          const newHighlights: {
            text: string;
            image?: {
              url: string;
              s3_key: string;
              title: string;
              caption: string;
            };
          }[] = [];

          newHighlights.push({ text: String(respObj.title || "") });
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
            newHighlights.push({ text, image });
          });

          setSummary({
            ...summary,
            title: String(respObj.title || ""),
            highlights: newHighlights,
          });

          // Exclude the title (index 0) from table rows while preserving
          // the original `order` indices on each row.
          const mapped = newHighlights
            .map((h, id) => ({
              order: id,
              text: h.text,
              image: normalizeImageUrl(h.image?.url) || null,
              imageCaption: String(h.image?.caption ?? ""),
            }))
            .filter((r) => r.order > 0);
          setRowData(mapped);
        } else {
          alert("No highlights found in the crawled content.");
        }
        setLoading(false);
      }
    } catch (err: unknown) {
      console.error(err);
      const msg = err instanceof Error ? err.message : String(err);
      alert(`Error crawling URL: ${msg}`);
      setLoading(false);
    }
  };

  const router = useRouter();

  const onSubmit = async () => {
    setLoading(true);
    const isFormValid = await trigger();
    if (isFormValid) {
      router.push("video");
    }
    setLoading(false);
  };

  if (!isMounted) return null;

  return (
    <>
      <form onSubmit={handleSubmit(onSubmit)}>
        <Box display={"flex"} flexDirection={"column"} gap={3} marginBottom={5}>
          {/* --- Controls: Model / Temperature / Number of Words per Highlight --- */}
          <Accordion
            expanded={configExpanded}
            onChange={() => setConfigExpanded((s) => !s)}
          >
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                CONFIGURATION
              </Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Paper elevation={1} sx={{ padding: 2 }}>
                {/* Controls split into two rows: first row has 3 controls, second row has 2 controls. */}
                <Box display="flex" flexDirection="column" gap={2}>
                  <Box
                    display="flex"
                    gap={2}
                    alignItems="center"
                    sx={{
                      flexWrap: "nowrap",
                      overflowX: { xs: "auto", sm: "visible" },
                      justifyContent: "space-between",
                    }}
                  >
                    <Box sx={{ minWidth: 240, flex: "0 0 auto" }}>
                      <Typography variant="body2" sx={{ mb: 1, fontWeight: 700 }}>
                        AI Model
                      </Typography>
                      <Select
                        fullWidth
                        value={modelId}
                        onChange={(e) => setModelId(String(e.target.value))}
                        size="small"
                      >
                        {availableModelOptions.map((opt) => (
                          <MenuItem key={opt.value} value={opt.value}>
                            {opt.label}
                          </MenuItem>
                        ))}
                      </Select>
                    </Box>

                    <Box sx={{ width: 200, flex: "0 0 auto" }}>
                      <Typography variant="body2" sx={{ mb: 1, fontWeight: 700 }}>
                        Creativity (Temperature): {temperatureValue}
                      </Typography>
                      <Slider
                        min={0}
                        max={1}
                        step={0.1}
                        value={temperatureValue}
                        onChange={(_, v) =>
                          setTemperatureValue(
                            Array.isArray(v) ? v[0] : (v as number),
                          )
                        }
                        valueLabelDisplay="auto"
                      />
                    </Box>

                    <Box sx={{ width: 200, flex: "0 0 auto" }}>
                      <Typography variant="body2" sx={{ mb: 1, fontWeight: 700 }}>
                        Number of Highlights: {numHighlights}
                      </Typography>
                      <Slider
                        min={3}
                        max={5}
                        step={1}
                        value={numHighlights}
                        onChange={(_, v) =>
                          setNumHighlights(
                            Array.isArray(v) ? v[0] : (v as number),
                          )
                        }
                        valueLabelDisplay="auto"
                      />
                    </Box>
                  </Box>

                  <Box
                    display="flex"
                    gap={2}
                    alignItems="center"
                    sx={{
                      flexWrap: "nowrap",
                      overflowX: { xs: "auto", sm: "visible" },
                      justifyContent: "space-between",
                      // alignContent: "center",git ad
                    }}
                  >
                    <Box sx={{ minWidth: 150, flex: "1 1 0" }}>
                      <Typography variant="body2" sx={{ mb: 1, fontWeight: 700 }}>
                        Max Words per Segment
                      </Typography>
                      <TextField
                        size="small"
                        type="number"
                        inputProps={{ min: 1, max: 60 }}
                        value={wordsPerHighlight}
                        onChange={(e) =>
                          setWordsPerHighlight(Number(e.target.value || 0))
                        }
                      />
                    </Box>

                    <Box sx={{ maxWidth: 200, flex: "1 1 0" }}>
                      <Typography variant="body2" sx={{ mb: 1, fontWeight: 700 }}>
                        Summary Tone
                      </Typography>
                      <Select
                        fullWidth
                        value={summaryTone}
                        onChange={(e) => setSummaryTone(String(e.target.value))}
                        size="small"
                      >
                        {availableToneOptions.map((opt) => (
                          <MenuItem key={opt.value} value={opt.value}>
                            {opt.label}
                          </MenuItem>
                        ))}
                      </Select>
                    </Box>
                  </Box>
                </Box>

                <Box
                  sx={{
                    display: "flex",
                    justifyContent: "center",
                    mt: 2,
                    width: "100%",
                    flexBasis: "100%",
                  }}
                >
                  <Button
                    variant="contained"
                    onClick={generateHighlights}
                    disabled={loading}
                    sx={{ width: { xs: "90%", sm: "auto" } }}
                  >
                    Generate
                  </Button>
                </Box>
              </Paper>
            </AccordionDetails>
          </Accordion>

          {!!highlights?.length && (
            <Accordion
              expanded={highlightsExpanded}
              onChange={() => setHighlightsExpanded((s) => !s)}
            >
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                  HIGHLIGHTS
                </Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Paper elevation={1} sx={{ padding: 2, mb: 2 }}>
                  <Typography variant="body2" sx={{ mb: 1, fontWeight: 700 }}>
                    Title
                  </Typography>
                  <TextField
                    fullWidth
                    size="small"
                    value={summary.title || ""}
                    onChange={(e) => {
                      const newTitle = String(e.target.value || "");
                      const nextHighlights = Array.isArray(summary.highlights)
                        ? structuredClone(summary.highlights)
                        : [];
                      if (nextHighlights.length === 0) {
                        nextHighlights.unshift({ text: newTitle });
                      } else {
                        const existing = nextHighlights[0] || {};
                        nextHighlights[0] = {
                          ...existing,
                          text: newTitle,
                        };
                      }
                      setSummary({
                        ...summary,
                        title: newTitle,
                        highlights: nextHighlights,
                      });
                    }}
                  />
                </Paper>

                <Paper elevation={2}>
                  {loading ? (
                    <Box sx={{ p: 2 }}>
                      {/* Show 3 skeleton rows approximating the DataGrid layout */}
                      {[0, 1, 2, 3].map((i) => (
                        <Box
                          key={i}
                          display="flex"
                          gap={2}
                          alignItems="center"
                          sx={{ mb: 2 }}
                        >
                          <Skeleton
                            variant="rectangular"
                            width={60}
                            height={32}
                          />
                          <Box sx={{ flex: 1 }}>
                            <Skeleton variant="text" width="80%" />
                            <Skeleton variant="text" width="60%" />
                          </Box>
                          <Skeleton
                            variant="rectangular"
                            width={120}
                            height={80}
                          />
                        </Box>
                      ))}
                    </Box>
                  ) : (
                    <DataGrid
                      rows={rowData}
                      getRowId={({ order }) => order}
                      columns={columns}
                      getRowHeight={() => "auto"}
                      initialState={{
                        pagination: {
                          paginationModel: {
                            pageSize: 10,
                          },
                        },
                      }}
                      pageSizeOptions={[10]}
                      // checkboxSelection
                      processRowUpdate={(newRow) => {
                        updateRow(newRow);
                        return newRow;
                      }}
                      sx={{
                        "& .MuiDataGrid-cell": {
                          paddingY: 2, // Adds vertical padding to rows
                        },
                      }}
                      loading={loading}
                    />
                  )}
                </Paper>
              </AccordionDetails>
            </Accordion>
          )}
          <Box display={"flex"} justifyContent={"space-between"}>
            <Button variant="contained" onClick={() => router.push("home")}>
              Go Back
            </Button>
            {!!highlights?.length && (
              <Button variant="contained" type="submit" disabled={loading}>
                Continue
              </Button>
            )}
          </Box>
        </Box>
      </form>
      {/* Dummy determinate progress bar shown while loading */}
      {loading && (
        <Backdrop
          open={loading}
          sx={{ zIndex: (theme) => theme.zIndex.drawer + 2, color: "#fff" }}
        >
          <Box sx={{ width: "80%", maxWidth: 800 }}>
            <LinearProgress variant="determinate" value={progress} />
            <Box display="flex" justifyContent="center" sx={{ py: 1 }}>
              <Typography variant="body2">
                Reading your link and generating highlights...{" "}
                {Math.round(progress)}%
              </Typography>
            </Box>
          </Box>
        </Backdrop>
      )}
    </>
  );
}
