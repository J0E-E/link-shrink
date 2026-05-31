import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

// Self-hosted Inter (no external font CDN). Tokens must load before global so the
// custom properties exist when the base styles reference them.
import "@fontsource/inter/400.css";
import "@fontsource/inter/500.css";
import "@fontsource/inter/600.css";
import "./styles/tokens.css";
import "./styles/global.css";

import App from "./App";

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("Root element #root was not found in the document.");
}

createRoot(rootElement).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
);
