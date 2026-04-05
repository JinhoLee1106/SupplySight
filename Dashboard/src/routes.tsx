import { createBrowserRouter } from "react-router";
import { Layout } from "./components/Layout";
import { Dashboard } from "./components/Dashboard";
import { Rules } from "./components/Rules";
import { Reports } from "./components/Reports";
import { Database } from "./components/Database";

export const router = createBrowserRouter([
  {
    path: "/",
    Component: Layout,
    children: [
      { index: true, Component: Dashboard },
      { path: "rules", Component: Rules },
      { path: "reports", Component: Reports },
      { path: "database", Component: Database },
    ],
  },
]);
