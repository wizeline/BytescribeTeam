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
} from "@mui/material";
import * as yup from "yup";
import { yupResolver } from "@hookform/resolvers/yup";
import { useContext, useMemo, useState } from "react";
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
              .max(255, "Highlight text can't be longer than 255 characters")
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

export default function HighlightsTable() {
  const { summary, setSummary } = useContext(ArticleSummaryContext);
  const { highlights } = summary;

  const imageList = (highlights || [])
    .map(({ image }) => image)
    .filter((image) => !!image);

  const [rowData, setRowData] = useState(
    (highlights || []).map(({ text, image }, id) => ({
      order: id,
      text: text,
      image: image?.url || null,
      imageCaption: image?.caption,
    })),
  );

  const [loading, setLoading] = useState(false);

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
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={value || placeHolderImg}
            alt={row.imageCaption || ""}
            width={120}
            height={80}
            // priority
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
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={url}
                  alt={caption}
                  width={120}
                  height={80}
                  // priority
                />
              </MenuItem>
            ))}
          </Select>
        ),
      },
    ],
    [errors.items, fields, imageList],
  );

  const router = useRouter();

  const apiUrl = process.env.NEXT_PUBLIC_ELEVENLABS_API;

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
      body: JSON.stringify({ highlights: payload }),
    })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`Request failed with ${response.status}`);
        }

        const data = await response.json();
        const videoId = data.body?.id;
        if (!videoId) {
          throw new Error(`Cannot get video id. Please try again later.`);
        }
        router.push(`video/${videoId}`);
      })
      .catch((err) => {
        console.error(err);
        alert(`Error sending URL: ${err.message || err}`);
      })
      .finally(() => {
        setLoading(false);
      });
  };

  const { palette } = useTheme();

  return (
    <>
      <form onSubmit={handleSubmit(onSubmit)}>
        <Box display={"flex"} flexDirection={"column"} gap={3} marginBottom={5}>
          {!highlights?.length ? (
            <Box textAlign={"center"} py={4}>
              No data found. Go back and try again
            </Box>
          ) : (
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
