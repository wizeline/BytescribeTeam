"use client";
import { ArticleSummaryContext } from "@/contexts/ArticleSummary";
import { Box, BoxProps, Button, InputLabel, TextField } from "@mui/material";
import { useRouter } from "next/navigation";
import { useContext, useState } from "react";
import { Controller, useForm } from "react-hook-form";

export default function UrlBox(props: BoxProps) {
  const {
    control,
    handleSubmit,
    formState: { isValid, errors },
  } = useForm({
    defaultValues: {
      urlPath: "",
    },
    mode: "onChange",
  });

  const [loading] = useState(false);
  const router = useRouter();

  const { setSummary } = useContext(ArticleSummaryContext);

  // Simplified submit: store the provided URL in the shared ArticleSummary
  // context and navigate to the adjust page. The actual crawl/generation
  // will be performed later by the Generate button in HighlightsTable.
  const onSubmit = async (data: { urlPath: string }) => {
    const { urlPath } = data;
    // Store the raw URL in summary for downstream usage
    setSummary({ title: "", highlights: [], url: encodeURI(urlPath) });
    router.push("adjust");
  };

  // No theme usage required here

  // No polling or backend calls here anymore — UrlBox simply stores the URL
  // into the article summary and navigates to the adjust UI.

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
              <InputLabel htmlFor="input-url">Confluence Link: </InputLabel>
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
                    disabled={loading}
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
            disabled={loading || !isValid}
            sx={{ alignSelf: "end" }}
          >
            Next
          </Button>
          {/* (async submission only) */}
        </Box>
      </form>
      {/* UrlBox is a simple URL input now; UI for background processing happens elsewhere */}
    </>
  );
}
