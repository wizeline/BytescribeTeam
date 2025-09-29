import { createContext } from "react";

export type ArticleSummary = {
  id?: string;
  title?: string;
  highlights?: {
    text: string;
    image?: { src: string };
  }[];
};

export const ArticleSummaryContext = createContext<{
  summary: ArticleSummary;
  setSummary: (value: ArticleSummary) => void;
}>({
  summary: {},
  setSummary: () => {},
});
