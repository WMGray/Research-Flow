import { RouterProvider } from "react-router-dom";
import { DialogProvider } from "@/components/ui/DialogProvider";
import { router } from "@/router";

export default function App() {
  return (
    <DialogProvider>
      <RouterProvider router={router} />
    </DialogProvider>
  );
}
