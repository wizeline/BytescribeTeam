"use client";

import Image from "next/image";
import { DataGrid, GridColDef } from "@mui/x-data-grid";
import { useFieldArray, useForm } from "react-hook-form";
import { Box, Button, ButtonGroup, FormHelperText, Paper } from "@mui/material";
import * as yup from "yup";
import { yupResolver } from "@hookform/resolvers/yup";
import { useMemo } from "react";

const schema = yup
  .object({
    items: yup
      .array()
      .of(
        yup
          .object({
            order: yup.number().required("ID must be required"),
            highlights: yup
              .string()
              .max(128, "Highlight text can't be longer than 128 characters")
              .required("Highlights is required"),
            images: yup.array().of(yup.string().required()),
          })
          .required(),
      )
      .required(),
  })
  .required();

const rowData = [
  {
    order: 1,
    highlights: "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
    images: ["https://picsum.photos/120/80"],
  },
  {
    order: 2,
    highlights:
      "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
    images: ["https://picsum.photos/120/80"],
  },
  {
    order: 3,
    highlights:
      "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.",
    images: ["https://picsum.photos/120/80"],
  },
  {
    order: 4,
    highlights:
      "Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.",
    images: [],
  },
  {
    order: 5,
    highlights:
      "Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.",
    images: ["https://picsum.photos/120/80"],
  },
];

export default function HighlightsTable() {
  const {
    control,
    handleSubmit,
    getValues,
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
    const fieldIndex = fields.findIndex(
      (field) => newRowValue.order === field.order,
    );
    update(fieldIndex, newRowValue);
    trigger();
  };

  const onSubmit = async () => {
    const isFormValid = await trigger();
    if (isFormValid) {
      alert(`Form is valid: ${JSON.stringify(getValues())}`);
    }
  };

  const columns: GridColDef<(typeof rowData)[number]>[] = useMemo(
    () => [
      { field: "order", headerName: "", width: 90 },
      {
        field: "highlights",
        headerName: "Highlights",
        flex: 1,
        editable: true,
        renderCell: ({ value, row }) => {
          const index = fields.findIndex((field) => row.order === field.order);
          return (
            <Box position={"relative"} height={"100%"}>
              {value}
              {errors.items && errors.items[index]?.highlights && (
                <FormHelperText
                  error
                  sx={{ position: "absolute", bottom: "-1rem" }}
                >
                  {errors.items[index]?.highlights.message || "Field is error"}
                </FormHelperText>
              )}
            </Box>
          );
        },
      },
      {
        field: "images",
        headerName: "Images",
        width: 150,
        editable: true,
        renderCell: ({ value, row }) =>
          value ? (
            <>
              {(value as string[]).map((url, id) => (
                <Image
                  key={`img${row.order}-${id}`}
                  src={url}
                  alt={row.highlights}
                  width={120}
                  height={80}
                  priority
                />
              ))}
            </>
          ) : null,
      },
    ],
    [errors, fields],
  );

  return (
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
            updateRow(newRow);
            return newRow;
          }}
          sx={{
            "& .MuiDataGrid-cell": {
              paddingY: 2, // Adds vertical padding to rows
            },
          }}
        />
      </Paper>
      <ButtonGroup variant="contained" sx={{ alignSelf: "end" }}>
        <Button>Go Back</Button>
        <Button onClick={() => !errors.items && onSubmit()}>Continue</Button>
      </ButtonGroup>
    </Box>
  );
}
