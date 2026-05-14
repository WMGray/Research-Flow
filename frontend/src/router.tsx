import { createBrowserRouter } from "react-router-dom";
import { MainLayout } from "@/layouts/MainLayout";
import { AcquirePage } from "@/pages/AcquirePage";
import { ConfigPage } from "@/pages/ConfigPage";
import { DiscoverPage } from "@/pages/DiscoverPage";
import { HomePage } from "@/pages/HomePage";
import { LibraryPage } from "@/pages/LibraryPage";
import { PaperDetailPage } from "@/pages/PaperDetailPage";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <MainLayout />,
    children: [
      { index: true, element: <HomePage /> },
      { path: "discover", element: <DiscoverPage /> },
      { path: "acquire", element: <AcquirePage /> },
      { path: "library", element: <LibraryPage /> },
      { path: "library/:paperId", element: <PaperDetailPage /> },
      { path: "config", element: <ConfigPage /> },
    ],
  },
]);
