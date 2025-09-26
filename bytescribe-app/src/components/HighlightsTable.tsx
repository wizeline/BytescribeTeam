"use client";

import Image from "next/image";
import { DataGrid, GridColDef } from "@mui/x-data-grid";
import { useFieldArray, useForm } from "react-hook-form";
import {
  Box,
  Button,
  ButtonGroup,
  FormHelperText,
  MenuItem,
  Paper,
  Select,
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
              .max(128, "Highlight text can't be longer than 128 characters")
              .required("Highlights is required"),
            image: yup.string(),
          })
          .required(),
      )
      .required(),
  })
  .required();

const placeHolderImg = "https://picsum.photos/120/80";

export default function HighlightsTable() {
  const {
    summary: { highlights },
    setSummary,
  } = useContext(ArticleSummaryContext);

  const [rowData, setRowData] = useState((highlights || []).map(({ text, image }, id) => ({
    order: id,
    text: text,
    image: image?.src || "",
  })));

  const [loading, setLoading] = useState(false);

  const {
    control,
    handleSubmit,
    trigger,
    formState: { errors },
  } = useForm({
    defaultValues: {
      items: rowData,
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

    const fieldIndex = fields.findIndex(
      (field) => newRowValue.order === field.order,
    );
    update(fieldIndex, newRowValue);
    trigger();
  };

  const apiUrl = process.env.NEXT_PUBLIC_ELEVENLABS_API;

  const onSubmit = async (data) => {
    console.log(data)
    const payload = data;
    fetch(apiUrl!, {
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
      const highlights = (
        data.summary.result.outputTextArray as string[]
      ).map((value, i) => {
        return {
          text: value,
          image: data.images[i],
        };
      });
      console.log(highlights);
      setSummary({
        title: data.title,
        highlights: highlights,
      });

      router.push("editing");
    })
    .catch((err) => {
      console.error(err);
      alert(`Error sending URL: ${err.message || err}`);
    })
    .finally(() => {
      setLoading(false);
    });
  };

  const columns: GridColDef<(typeof rowData)[number]>[] = useMemo(
    () => [
      { field: "order", headerName: "", width: 90 },
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
        renderCell: ({ value, row }) =>
          value ? (
            <img
              src={value}
              alt={row.text}
              width={120}
              height={80}
              // priority
            />
          ) : null,
        renderEditCell: ({ id, value, api, field }) => (
          <Select
            labelId="demo-simple-select-label"
            id="demo-simple-select"
            value={value}
            label=""
            fullWidth
            onChange={(event) => {
              console.log(event);
              // Update the cell value in the DataGrid's state
              api.setEditCellValue({
                id: id,
                field: field,
                value: event.target.value,
              });
            }}
          >
            {(highlights || [])
              .map(({ image }) => image)
              .filter((image) => !!image)
              .map(({ src }, id) => (
                <MenuItem key={`${src}-${id}`} value={src}>
                  <img
                    src={src}
                    alt={"Article Picture"}
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
    [errors.items, fields],
  );

  const router = useRouter();

  if (!apiUrl) {
    alert("Lambda API URL not configured. Set NEXT_PUBLIC_CRAWLER_API.");
    return;
  }

  if (!highlights) {
    alert("No data found. Go back and try again");
    return;
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <Box display={"flex"} flexDirection={"column"} gap={2}>
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
            checkboxSelection
            processRowUpdate={(newRow) => {
              console.log(newRow);
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
        <ButtonGroup variant="contained" sx={{ alignSelf: "end" }}>
          <Button onClick={() => router.push("home")}>Go Back</Button>
          <Button type="submit" disabled={loading}>Continue</Button>
        </ButtonGroup>
      </Box>
    </form>
  );
}
