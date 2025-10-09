"use client";

import Image from "next/image";
import { DataGrid, GridColDef } from "@mui/x-data-grid";
import { useFieldArray, useForm } from "react-hook-form";
import {
  Backdrop,
  Box,
  Button,
  CircularProgress,
  FormHelperText,
  MenuItem,
  Paper,
  Select,
  Typography,
  useTheme,
  TextField,
  Slider,
} from "@mui/material";
import * as yup from "yup";
import { yupResolver } from "@hookform/resolvers/yup";
import { useCallback, useContext, useEffect, useMemo, useState } from "react";
import { ArticleSummaryContext } from "@/contexts/ArticleSummary";
import { useRouter } from "next/navigation";

const apiUrl = process.env.NEXT_PUBLIC_ELEVENLABS_API;

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

export default function HighlightsTable() {
  const { summary, setSummary } = useContext(ArticleSummaryContext);
  const { highlights } = summary;

  console.log("summary", summary);

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

  const imageList = (highlights || [])
    .map(({ image }) =>
      image
        ? {
            ...image,
            url: normalizeImageUrl(image.url) || "",
            title: String(image.title ?? ""),
            caption: String(image.caption ?? ""),
            s3_key: image.s3_key ?? "",
          }
        : null,
    )
    .filter((image) => !!image) as {
    url: string;
    caption: string;
    title: string;
    s3_key: string;
  }[];

  const [rowData, setRowData] = useState(
    (highlights || []).map(({ text, image }, id) => ({
      order: id,
      text: text,
      image: normalizeImageUrl(image?.url) || null,
      imageCaption: String(image?.caption ?? ""),
    })),
  );

  const [loading, setLoading] = useState(false);
  // UI controls for generating highlights
  const [modelId, setModelId] = useState("");
  const [temperatureValue, setTemperatureValue] = useState<number>(0.7);
  const [wordsPerHighlight, setWordsPerHighlight] = useState<number>(30);

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
      ? imageList.find(({ url }) => newRowValue.image === url)
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
        renderEditCell: ({ id, value, api, field }) => (
          <Select
            labelId="demo-simple-select-label"
            id="demo-simple-select"
            value={value || placeHolderImg}
            label=""
            fullWidth
            onChange={(event) => {
              // Update the cell value in the DataGrid's state
              api.setEditCellValue({
                id: id,
                field: field,
                value: event.target.value,
              });
            }}
          >
            {imageList.map(({ url, caption }, id) => (
              <MenuItem key={`${url}-${id}`} value={url}>
                <Image
                  src={url}
                  alt={caption || "image"}
                  width={120}
                  height={80}
                  priority
                />
              </MenuItem>
            ))}
          </Select>
        ),
      },
    ],
    [errors.items, fields, imageList],
  );

  const [jobId, setJobId] = useState("");
  const [jobStatus, setJobStatus] = useState("");

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

        const data = await response.json();
        result = data.body;
      })
      .catch((err) => {
        console.error(err);
        result = `Error sending URL: ${err.message || err}`;
      });

    return result;
  }, [jobId]);

  const fetchHighlights = useCallback(async () => {
    setLoading(true);

    const start = Date.now();
    const intervalId = setInterval(async () => {
      // Check if timeout reached
      if (Date.now() - start >= 60000) {
        console.log("Sorry, timeout.");
        clearInterval(intervalId);
        setLoading(false);
        return;
      }

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const job: any = await fetchJob();
      console.log("job", job);

      if (job.status === "completed") {
        setJobStatus("completed");
        setLoading(false);
        clearInterval(intervalId);
      }
    }, 10000);
  }, [fetchJob]);

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
        maxTokenCount: 2048, // Default token count
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

                  const mapped = newHighlights.map((h, id) => ({
                    order: id,
                    text: h.text,
                    image: normalizeImageUrl(h.image?.url) || null,
                    imageCaption: String(h.image?.caption ?? ""),
                  }));
                  setRowData(mapped);
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

          const mapped = newHighlights.map((h, id) => ({
            order: id,
            text: h.text,
            image: normalizeImageUrl(h.image?.url) || null,
            imageCaption: String(h.image?.caption ?? ""),
          }));
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

  useEffect(() => {
    if (!!jobId) {
      if (jobStatus === "completed") {
        router.push(`video/${jobId}`);
      } else {
        fetchHighlights();
      }
    }
  }, [fetchHighlights, jobId, jobStatus, router]);

  const onSubmit = async (data: {
    items: (Omit<(typeof rowData)[0], "image" | "imageCaption"> & {
      image: string | null;
    })[];
  }) => {
    if (!apiUrl) {
      alert("Lambda API URL not configured. Set NEXT_PUBLIC_ELEVENLABS_API.");
      return;
    }

    setLoading(true);

    const payload = data.items.map((highlight) => {
      const highlightImg = highlight.image
        ? {
            src: highlight.image,
            s3_key:
              imageList.find(({ url }) => highlight.image === url)?.s3_key ||
              "",
          }
        : {};

      return {
        ...highlight,
        image: highlightImg,
      };
    });

    fetch(apiUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ highlights: payload, async: true }),
    })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`Request failed with ${response.status}`);
        }

        const data = await response.json();
        const jobId = data.body?.job_id;
        if (!jobId) {
          throw new Error(`No job id return. Please try again later.`);
        }

        setJobId(jobId);
        setJobStatus("processing");
      })
      .catch((err) => {
        console.error(err);
        alert(`Error sending URL: ${err.message || err}`);
        setLoading(false);
      });
  };

  const { palette } = useTheme();

  return (
    <>
      <form onSubmit={handleSubmit(onSubmit)}>
        <Box display={"flex"} flexDirection={"column"} gap={3} marginBottom={5}>
          {/* --- Controls: Model / Temperature / Number of Words per Highlight --- */}
          <Paper elevation={1} sx={{ padding: 2 }}>
            <Box display="flex" gap={2} flexWrap="wrap" alignItems="center">
              <Box sx={{ minWidth: 240 }}>
                <Typography variant="body2" sx={{ mb: 1 }}>
                  Model:
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

              <Box sx={{ width: 220 }}>
                <Typography variant="body2" sx={{ mb: 1 }}>
                  Temperature: {temperatureValue}
                </Typography>
                <Slider
                  min={0}
                  max={1}
                  step={0.1}
                  value={temperatureValue}
                  onChange={(_, v) =>
                    setTemperatureValue(Array.isArray(v) ? v[0] : (v as number))
                  }
                  valueLabelDisplay="auto"
                />
              </Box>

              <Box sx={{ minWidth: 160 }}>
                <Typography variant="body2" sx={{ mb: 1 }}>
                  Number of Words/Highlight
                </Typography>
                <TextField
                  size="small"
                  type="number"
                  inputProps={{ min: 1 }}
                  value={wordsPerHighlight}
                  onChange={(e) =>
                    setWordsPerHighlight(Number(e.target.value || 0))
                  }
                />
              </Box>

              <Box sx={{ ml: "auto" }}>
                <Button
                  variant="outlined"
                  onClick={generateHighlights}
                  disabled={loading}
                >
                  Generate
                </Button>
              </Box>
            </Box>
          </Paper>

          {!!highlights?.length && (
            <Paper elevation={2}>
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
            </Paper>
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
      <Backdrop
        open={loading}
        sx={palette.mode === "dark" ? { bgcolor: "rgba(0, 0, 0, 0.9)" } : {}}
      >
        <Box display={"flex"} gap={2} alignItems={"center"}>
          <CircularProgress color="inherit" />
          <Typography variant="h6">Generating media...</Typography>
        </Box>
      </Backdrop>
    </>
  );
}
