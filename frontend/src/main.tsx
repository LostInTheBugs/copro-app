import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { installDesktopDownloadBridge } from "./desktop";
import "./index.css";

// Version de bureau (Windows) : exports PDF/CSV via « Enregistrer sous » natif.
installDesktopDownloadBridge();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
);
