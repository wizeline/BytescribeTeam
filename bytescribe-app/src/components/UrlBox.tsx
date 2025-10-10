"use client";
import { ArticleSummaryContext } from "@/contexts/ArticleSummary";
import {
  Box,
  BoxProps,
  Button,
  TextField,
  Typography,
  Paper,
  InputAdornment,
  IconButton,
} from "@mui/material";
import CancelIcon from "@mui/icons-material/Cancel";
import { useRouter } from "next/navigation";
import { useContext, useState } from "react";
import { Controller, useForm } from "react-hook-form";

export default function UrlBox(props: BoxProps) {
  const { setSummary, summary } = useContext(ArticleSummaryContext);

  const {
    control,
    handleSubmit,
    formState: { isValid },
  } = useForm({
    defaultValues: {
      urlPath: summary?.url ? decodeURI(String(summary.url)) : "",
    },
    mode: "onChange",
  });

  const [loading] = useState(false);
  const router = useRouter();

  const onSubmit = async (data: { urlPath: string }) => {
    const { urlPath } = data;
    setSummary({ ...summary, url: encodeURI(String(urlPath)) });
    router.push("adjust");
  };

  return (
    <>
      <Box sx={{ maxWidth: 900, mx: "auto", px: 2, py: 3 }} {...props}>
        <Paper
          elevation={0}
          sx={{
            boxShadow: 2,
            borderRadius: 2,
            p: 2,
            mb: 3,
            backgroundColor: (theme) => theme.palette.background.paper,
          }}
        >
          <Typography variant="subtitle1" color="text.secondary" gutterBottom>
            <b>INTRODUCTION</b>
          </Typography>
          <Typography variant="body1" sx={{ lineHeight: 1.4 }}>
            <Typography
              component="span"
              sx={{ color: "primary.main", fontWeight: "bold" }}
            >
              Page2Play
            </Typography>{" "}
            solution is your revolutionary antidote to organizational
            information overload. It offers a breakthrough way to transform
            lengthy, dense documentation into{" "}
            <Typography
              component="span"
              sx={{ color: "primary.main", fontWeight: "bold" }}
            >
              concise, engaging video summaries
            </Typography>
            , ensuring that critical knowledge is always accessible and easily
            shared across your teams. This approach will{" "}
            <Typography
              component="span"
              sx={{ color: "primary.main", fontWeight: "bold" }}
            >
              save user time, boost productivity, and accelerate knowledge
              adoption.
            </Typography>
            <br />
            <br />
            <Typography
              component="span"
              sx={{ color: "primary.main", fontWeight: "bold" }}
            >
              Enter your Confluence URL below to streamline your team's workflow
              and create shareable video content today!
            </Typography>
          </Typography>
        </Paper>

        <form onSubmit={handleSubmit(onSubmit)}>
          <Box
            display={"flex"}
            flexDirection={{ xs: "column", sm: "row" }}
            gap={2}
            alignItems={{ xs: "stretch", sm: "center" }}
          >
            <Box sx={{ flex: 1 }}>
              <Controller
                name="urlPath"
                control={control}
                render={({ field, fieldState }) => (
                  <TextField
                    id="input-url"
                    placeholder="https://wizeline.atlassian.net//path/to/page"
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
                    sx={{
                      boxShadow: 2,
                      borderRadius: 1,
                      "& .MuiOutlinedInput-root": {
                        "&.Mui-focused fieldset": {
                          borderColor: "primary.main",
                          boxShadow: "0 0 0 2px #1976d2", // Replace #1976d2 with your Primary Blue hex if different
                        },
                      },
                    }}
                    autoFocus
                    slotProps={{
                      input: {
                        startAdornment: (
                          <InputAdornment position="start">
                            Confluence Link:
                          </InputAdornment>
                        ),
                        endAdornment: field.value ? (
                          <InputAdornment position="end">
                            <IconButton
                              size="small"
                              aria-label="clear url"
                              onClick={() => {
                                // Clear the input value in the form
                                field.onChange("");
                              }}
                            >
                              <CancelIcon
                                sx={{ fontSize: 16, lineHeight: 1 }}
                              />
                            </IconButton>
                          </InputAdornment>
                        ) : undefined,
                      },
                    }}
                  />
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

            <Box sx={{ display: "flex", alignItems: "center" }}>
              <Button
                variant="contained"
                color="primary"
                type="submit"
                disabled={loading || !isValid}
                sx={{ height: 48, whiteSpace: "nowrap" }}
              >
                Next
              </Button>
            </Box>
          </Box>
        </form>
      </Box>
    </>
  );
}
