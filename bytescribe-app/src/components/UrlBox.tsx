"use client";
import {
  Backdrop,
  Box,
  BoxProps,
  CircularProgress,
  InputLabel,
  TextField,
} from "@mui/material";
import { useState } from "react";
import { Controller, useForm } from "react-hook-form";

export default function UrlBox(props: BoxProps) {
  const { control, handleSubmit } = useForm({
    defaultValues: {
      urlPath: "",
    },
    mode: "onChange",
  });

  const [loading, setLoading] = useState(false);

  const onSubmit = (data: { urlPath: string }) => {
    const { urlPath } = data;
    const payload = encodeURI(urlPath);

    setLoading(true);
    setTimeout(() => {
      alert(`User input: ${payload}`);
      setLoading(false);
    }, 1000);
  };

  return (
    <>
      <form onSubmit={handleSubmit(onSubmit)}>
        <Box {...props}>
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
                  sx={{ height: "3.5rem" }}
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
      </form>
      <Backdrop open={loading}>
        <CircularProgress color="inherit" />
      </Backdrop>
    </>
  );
}
