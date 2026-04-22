import { createBrowserRouter } from "react-router";
import { Layout } from "./components/Layout";
import { Dashboard } from "./components/Dashboard";
import { Products } from "./components/Products";
import { Rules } from "./components/Rules";
import { Database } from "./components/Database";
import { Agents } from "./components/Agents";

export const router = createBrowserRouter([
  {
    path: "/",
    Component: Layout,
    children: [
      { index: true, Component: Dashboard },
      { path: "products", Component: Products },
      { path: "rules", Component: Rules },
      { path: "database", Component: Database },
      { path: "agents", Component: Agents },
    ],
  },
]);
