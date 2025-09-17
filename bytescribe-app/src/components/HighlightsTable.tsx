"use client";

import Image from "next/image";
import { DataGrid, GridColDef } from "@mui/x-data-grid";

const columns: GridColDef<(typeof rows)[number]>[] = [
  { field: "id", headerName: "", width: 90 },
  {
    field: "highlights",
    headerName: "Highlights",
    flex: 1,
    editable: true,
  },
  {
    field: "images",
    headerName: "Images",
    width: 150,
    editable: true,
    renderCell: ({ value, row }) =>
      value ? (
        <Image
          src={value}
          alt={row.highlights}
          width={120}
          height={80}
          priority
        />
      ) : null,
  },
];

const rows = [
  {
    id: 1,
    highlights: "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
    images: "https://picsum.photos/120/80",
  },
  {
    id: 2,
    highlights:
      "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
    images: "https://picsum.photos/120/80",
  },
  {
    id: 3,
    highlights:
      "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.",
    images: "https://picsum.photos/120/80",
  },
  {
    id: 4,
    highlights:
      "Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.",
    images: "",
  },
  {
    id: 5,
    highlights:
      "Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.",
    images: "https://picsum.photos/120/80",
  },
];

export default function HighlightsTable() {
  return (
    <DataGrid
      rows={rows}
      columns={columns}
      initialState={{
        pagination: {
          paginationModel: {
            pageSize: 10,
          },
        },
      }}
      pageSizeOptions={[10]}
      checkboxSelection
      disableRowSelectionOnClick
    />
  );
}
