import { NavLink, Route, Routes } from "react-router-dom";

import { AlertQueuePage } from "./pages/AlertQueuePage";
import { CaseDetailPage } from "./pages/CaseDetailPage";
import { OverviewPage } from "./pages/OverviewPage";
import { RulesTuningPage } from "./pages/RulesTuningPage";
import "./App.css";

const NAV_ITEMS = [
  { to: "/", label: "Overview", end: true },
  { to: "/alerts", label: "Alert Queue" },
  { to: "/rules", label: "Rules & Tuning" },
];

export function App() {
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <span className="sidebar-brand-mark">AML</span>
          <span className="sidebar-brand-name">Alert Triage</span>
        </div>
        <nav className="sidebar-nav">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => `sidebar-link${isActive ? " sidebar-link-active" : ""}`}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <p>Synthetic data only.</p>
          <p>No production or personal data is used.</p>
        </div>
      </aside>
      <main className="content">
        <Routes>
          <Route path="/" element={<OverviewPage />} />
          <Route path="/alerts" element={<AlertQueuePage />} />
          <Route path="/alerts/:alertId" element={<CaseDetailPage />} />
          <Route path="/rules" element={<RulesTuningPage />} />
        </Routes>
      </main>
    </div>
  );
}
