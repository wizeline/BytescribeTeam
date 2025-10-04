"use client";
import { ArticleSummaryContext } from "@/contexts/ArticleSummary";
import {
  Backdrop,
  Box,
  BoxProps,
  Button,
  CircularProgress,
  InputLabel,
  TextField,
} from "@mui/material";
import { useRouter } from "next/navigation";
import { useContext, useState } from "react";
import { Controller, useForm } from "react-hook-form";

const MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0";

export default function UrlBox(props: BoxProps) {
  const { control, handleSubmit } = useForm({
    defaultValues: {
      urlPath: "",
    },
    mode: "onChange",
  });

  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const { setSummary } = useContext(ArticleSummaryContext);

  const onSubmit = (data: { urlPath: string }) => {
    const { urlPath } = data;
    const payload = {
      url: encodeURI(urlPath),
      full: true,
      model_id: MODEL_ID,
      text_config: {
        temperature: 0.7,
        maxTokenCount: 2048,
      },
    };

    const apiUrl = process.env.NEXT_PUBLIC_CRAWLER_API;
    const mediaUrl = process.env.NEXT_PUBLIC_S3_BUCKET;

    if (!apiUrl) {
      alert("Lambda API URL not configured. Set NEXT_PUBLIC_CRAWLER_API.");
      return;
    }

    setLoading(true);

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

        if (!data.summary.bullets.length) {
          throw new Error(
            `No data is return for this article. Try again later.`,
          );
        }

        const highlights = [];
        highlights.push({ text: data.title });

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (data.summary.bullets as any[]).map(
          (bullet: { text: string; image_url: { image_url: string }[] }) => {
            highlights.push({
              text: bullet.text,
              image: bullet.image_url[0]
                ? {
                    ...bullet.image_url[0],
                    s3_key: bullet.image_url[0].image_url.replace(
                      "s3://bytescribe-image-audio-bucket/",
                      "",
                    ),
                    url: bullet.image_url[0].image_url.replace(
                      "s3://bytescribe-image-audio-bucket",
                      mediaUrl || "",
                    ),
                  }
                : undefined,
            });
          },
        );

        setSummary({
          title: data.title,
          highlights: highlights,
        });

        router.push("adjust");
      })
      .catch((err) => {
        console.error(err);
        alert(`Error sending URL: ${err.message || err}`);
      })
      .finally(() => {
        setLoading(false);
      });
  };

  return (
    <>
      <form onSubmit={handleSubmit(onSubmit)}>
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
            disabled={loading}
            sx={{ alignSelf: "end" }}
          >
            Go
          </Button>
        </Box>
      </form>
      <Backdrop open={loading}>
        <CircularProgress color="inherit" />
      </Backdrop>
    </>
  );
}
