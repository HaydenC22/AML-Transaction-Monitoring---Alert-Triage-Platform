import type { ReactNode } from "react";

import "./PageHeader.css";

export function PageHeader({ eyebrow, title, action }: { eyebrow?: string; title: string; action?: ReactNode }) {
  return (
    <div className="page-header">
      <div>
        {eyebrow && <div className="page-header-eyebrow mono">{eyebrow}</div>}
        <h1 className="page-header-title">{title}</h1>
      </div>
      {action}
    </div>
  );
}
