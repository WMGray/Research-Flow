import { createBrowserRouter } from "react-router-dom";

import { HomePage } from "@/pages/HomePage";
import { LibraryPage } from "@/pages/LibraryPage";
import { ProjectsPage } from "@/pages/ProjectsPage";
import { DailyPage } from "@/pages/DailyPage";
import { ViewsPage } from "@/pages/ViewsPage";
import { DatasetsPage } from "@/pages/DatasetsPage";
import { MainLayout } from "@/layouts/MainLayout";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <MainLayout />,
    children: [
      {
        index: true,
        element: <HomePage />,
      },
      {
        path: "daily",
        element: <DailyPage />,
      },
      {
        path: "datasets",
        element: <DatasetsPage />,
      },
      {
        path: "library",
        element: <LibraryPage />,
      },
      {
        path: "projects",
        element: <ProjectsPage />,
      },
      {
        path: "views",
        element: <ViewsPage />,
      },
    ],
  },
]);
