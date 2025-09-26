import UrlBox from "@/components/UrlBox";
import { Container } from "@mui/material";

export default function StartPage() {
  return (
    <Container maxWidth="xl">
      <UrlBox minHeight={"calc(100vh - 338px)"}/>
    </Container>
  );
}
