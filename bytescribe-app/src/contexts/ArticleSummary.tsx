import { createContext } from "react";

export type ArticleSummary = {
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
