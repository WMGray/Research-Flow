import { Navigate } from "react-router-dom";

export function AcquirePage() {
  return <Navigate replace to="/discover?view=acquire" />;
}
