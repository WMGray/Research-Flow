import { Navigate, createHashRouter } from "react-router-dom";

import { MainLayout } from "@/layouts/MainLayout";
import { AcquirePage } from "@/pages/AcquirePage";
import { ArchivePage } from "@/pages/ArchivePage";
import { ConfigPage } from "@/pages/ConfigPage";
import { DiscoverPage } from "@/pages/DiscoverPage";
import { HomePage } from "@/pages/HomePage";
import { LibraryPage } from "@/pages/LibraryPage";
import { UncategorizedPage } from "@/pages/UncategorizedPage";

export const router = createHashRouter([
  {
    path: "/",
    element: <MainLayout />,
    children: [
      { index: true, element: <HomePage /> },
      { path: "discover", element: <DiscoverPage /> },
      { path: "acquire", element: <AcquirePage /> },
      { path: "library", element: <LibraryPage /> },
      { path: "library/:paperId", element: <LibraryPage /> },
      { path: "uncategorized", element: <UncategorizedPage /> },
      { path: "archive", element: <ArchivePage /> },
      { path: "settings", element: <ConfigPage /> },
      { path: "config", element: <Navigate replace to="/settings" /> },
    ],
  },
]);
