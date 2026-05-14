import { createBrowserRouter } from "react-router-dom";
import { MainLayout } from "@/layouts/MainLayout";
import { HomePage } from "@/pages/HomePage";
import { PlaceholderPage } from "@/pages/PlaceholderPage";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <MainLayout />,
    children: [
      { index: true, element: <HomePage /> },
      { path: "overview", element: <PlaceholderPage title="Papers Overview" /> },
      { path: "discover", element: <PlaceholderPage title="Discover" /> },
      { path: "acquire", element: <PlaceholderPage title="Acquire" /> },
      { path: "library", element: <PlaceholderPage title="Library" /> },
      { path: "runtime", element: <PlaceholderPage title="Runtime" /> },
      { path: "logs", element: <PlaceholderPage title="Logs" /> },
    ],
  },
]);
