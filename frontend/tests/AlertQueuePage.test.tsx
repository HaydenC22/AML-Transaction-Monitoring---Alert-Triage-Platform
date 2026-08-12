import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api, type AlertListResponse } from "../src/api/client";
import { AlertQueuePage } from "../src/pages/AlertQueuePage";
import { withProviders } from "./testUtils";

vi.mock("../src/api/client", async () => {
  return {
    api: {
      listAlerts: vi.fn(),
    },
  };
});

const BASE_ALERTS: AlertListResponse["items"] = [
  {
    alert_id: 1,
    transaction_key: "tx-1",
    transaction_type: "TRANSFER",
    amount: 500,
    origin_account_nk: "C1000000001",
    severity: "low",
    composite_score: 0.2,
    ml_anomaly_score: 0.1,
    is_fraud_label: false,
    created_at: "2026-01-01T00:00:00Z",
    status: "open",
    rule_flags: [],
  },
  {
    alert_id: 2,
    transaction_key: "tx-2",
    transaction_type: "CASH_OUT",
    amount: 9500,
    origin_account_nk: "C1000000002",
    severity: "critical",
    composite_score: 0.95,
    ml_anomaly_score: 0.9,
    is_fraud_label: true,
    created_at: "2026-01-02T00:00:00Z",
    status: "open",
    rule_flags: ["structuring", "velocity_spike"],
  },
  {
    alert_id: 3,
    transaction_key: "tx-3",
    transaction_type: "PAYMENT",
    amount: 3000,
    origin_account_nk: "C1000000003",
    severity: "medium",
    composite_score: 0.5,
    ml_anomaly_score: 0.4,
    is_fraud_label: false,
    created_at: "2026-01-03T00:00:00Z",
    status: "closed",
    rule_flags: ["high_risk_jurisdiction"],
  },
];

function mockListAlerts(items = BASE_ALERTS) {
  vi.mocked(api.listAlerts).mockResolvedValue({
    items,
    total: items.length,
    page: 1,
    page_size: 25,
  });
}

describe("AlertQueuePage", () => {
  beforeEach(() => {
    vi.mocked(api.listAlerts).mockReset();
  });

  it("renders each alert row with its severity and account", async () => {
    mockListAlerts();
    render(withProviders(<AlertQueuePage />));

    expect(await screen.findByText("C1000000001")).toBeInTheDocument();
    expect(screen.getByText("C1000000002")).toBeInTheDocument();
    expect(screen.getByText("C1000000003")).toBeInTheDocument();

    const table = screen.getByRole("table");
    expect(within(table).getByText("Critical")).toBeInTheDocument();
    expect(within(table).getByText("structuring")).toBeInTheDocument();
    expect(within(table).getByText("high risk jurisdiction")).toBeInTheDocument();
  });

  it("requests the severity filter param when changed", async () => {
    mockListAlerts();
    const user = userEvent.setup();
    render(withProviders(<AlertQueuePage />));

    await screen.findByText("C1000000001");

    const severitySelect = screen.getByLabelText("Severity");
    await user.selectOptions(severitySelect, "critical");

    await waitFor(() => {
      const lastCall = vi.mocked(api.listAlerts).mock.calls.at(-1)?.[0];
      expect(lastCall).toMatchObject({ severity: "critical", page: 1 });
    });
  });

  it("requests the rule filter param when changed", async () => {
    mockListAlerts();
    const user = userEvent.setup();
    render(withProviders(<AlertQueuePage />));

    await screen.findByText("C1000000001");

    const ruleSelect = screen.getByLabelText("Rule");
    await user.selectOptions(ruleSelect, "structuring");

    await waitFor(() => {
      const lastCall = vi.mocked(api.listAlerts).mock.calls.at(-1)?.[0];
      expect(lastCall).toMatchObject({ rule: "structuring" });
    });
  });

  it("sorts visible rows by amount when the Amount header is clicked", async () => {
    mockListAlerts();
    const user = userEvent.setup();
    render(withProviders(<AlertQueuePage />));

    await screen.findByText("C1000000001");

    const table = screen.getByRole("table");
    const amountHeaderButton = within(table).getByRole("button", { name: /Amount/ });

    await user.click(amountHeaderButton); // descending by amount
    let rows = within(table).getAllByRole("row").slice(1); // skip header row
    expect(within(rows[0]).getByText("C1000000002")).toBeInTheDocument(); // $9,500 highest

    await user.click(amountHeaderButton); // toggle to ascending
    rows = within(table).getAllByRole("row").slice(1);
    expect(within(rows[0]).getByText("C1000000001")).toBeInTheDocument(); // $500 lowest
  });

  it("shows an empty state when no alerts match", async () => {
    mockListAlerts([]);
    render(withProviders(<AlertQueuePage />));

    expect(await screen.findByText("No alerts match these filters.")).toBeInTheDocument();
  });
});
