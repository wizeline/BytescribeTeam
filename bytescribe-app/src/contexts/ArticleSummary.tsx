import { createContext } from "react";

export type ArticleSummary = {
  id?: string;
  title?: string;
  highlights?: {
    text: string;
    image?: {
      url: string;
      s3_key: string;
      title: string;
      caption: string;
    };
  }[];
};

export const ArticleSummaryContext = createContext<{
  summary: ArticleSummary;
  setSummary: (value: ArticleSummary) => void;
}>({
  summary: {},
  setSummary: () => {},
});
