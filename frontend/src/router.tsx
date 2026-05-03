import { createBrowserRouter } from "react-router-dom";

import { HomePage } from "@/pages/HomePage";
import { LibraryPage } from "@/pages/LibraryPage";
import { ProjectsPage } from "@/pages/ProjectsPage";
import { DailyPage } from "@/pages/DailyPage";
import { ViewsPage } from "@/pages/ViewsPage";
import { DatasetsPage } from "@/pages/DatasetsPage";
import { ConferencesPage } from "@/pages/ConferencesPage";
import { DiscoveryPage } from "@/pages/DiscoveryPage";
import { SettingsPage } from "@/pages/SettingsPage";
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
        path: "conferences",
        element: <ConferencesPage />,
      },
      {
        path: "discovery",
        element: <DiscoveryPage />,
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
        path: "settings",
        element: <SettingsPage />,
      },
      {
        path: "views",
        element: <ViewsPage />,
      },
    ],
  },
]);
