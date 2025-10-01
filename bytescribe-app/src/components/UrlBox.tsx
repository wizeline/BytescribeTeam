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
      text_config: { temperature: 0.7, maxTokenCount: 2048 },
    };

    const apiUrl = process.env.NEXT_PUBLIC_CRAWLER_API;

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
        const highlights = [];
        const uploaded_media = data.uploaded_media || [];

        const imgList = (data.images as Record<"string", "string">[]).map(
          (image, id) => ({
            ...image,
            ...(uploaded_media[id] || {}),
          }),
        );

        highlights.push({ text: data.title });
        (data.summary.result.outputTextArray as string[]).map((value, i) => {
          highlights.push({
            text: value,
            image: imgList[i],
          });
        });

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
