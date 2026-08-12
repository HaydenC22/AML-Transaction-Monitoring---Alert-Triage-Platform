import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api, type AlertDetail } from "../src/api/client";
import { CaseDetailPage } from "../src/pages/CaseDetailPage";
import { withRoute } from "./testUtils";

vi.mock("../src/api/client", async () => {
  return {
    api: {
      getAlert: vi.fn(),
      getCaseTimeline: vi.fn(),
      dispositionAlert: vi.fn(),
      addNote: vi.fn(),
    },
  };
});

const BASE_ALERT: AlertDetail = {
  alert_id: 42,
  transaction_key: "abcdef0123456789",
  transaction_type: "TRANSFER",
  amount: 9320.34,
  origin_account_nk: "C1483511640",
  severity: "critical",
  composite_score: 1.0,
  ml_anomaly_score: 0.99,
  is_fraud_label: true,
  created_at: "2026-01-01T00:00:00Z",
  status: "open",
  rule_flags: ["structuring", "velocity_spike"],
  origin_geography_key: "3e8d115e-aaaa",
  dest_geography_key: "0f177369-bbbb",
  account_history: [],
  disposition: null,
  notes: [],
};

function renderCaseDetail(alert: AlertDetail = BASE_ALERT) {
  vi.mocked(api.getAlert).mockResolvedValue(alert);
  vi.mocked(api.getCaseTimeline).mockResolvedValue([]);
  return render(withRoute(<CaseDetailPage />, "/alerts/:alertId", `/alerts/${alert.alert_id}`));
}

describe("CaseDetailPage", () => {
  beforeEach(() => {
    vi.mocked(api.getAlert).mockReset();
    vi.mocked(api.getCaseTimeline).mockReset();
    vi.mocked(api.dispositionAlert).mockReset();
    vi.mocked(api.addNote).mockReset();
  });

  it("renders transaction context and triggered rule explanations", async () => {
    renderCaseDetail();

    expect(await screen.findByText("$9,320.34")).toBeInTheDocument();
    expect(screen.getByText("structuring")).toBeInTheDocument();
    expect(screen.getByText("velocity spike")).toBeInTheDocument();
    expect(
      screen.getByText(/Several transfers just under a round reporting threshold/)
    ).toBeInTheDocument();
  });

  it("shows the ML-only explanation when no rules triggered", async () => {
    renderCaseDetail({ ...BASE_ALERT, rule_flags: [] });

    expect(
      await screen.findByText(/surfaced by the Isolation Forest anomaly score alone/)
    ).toBeInTheDocument();
  });

  it("shows the disposition form when the alert is undispositioned", async () => {
    renderCaseDetail();

    expect(await screen.findByLabelText("Analyst ID")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Submit disposition" })).toBeInTheDocument();
  });

  it("shows the disposition summary instead of the form once dispositioned", async () => {
    renderCaseDetail({
      ...BASE_ALERT,
      status: "closed",
      disposition: {
        disposition_id: 1,
        analyst_id: "jane.doe",
        outcome: "true_positive",
        rationale_notes: "Confirmed structuring pattern.",
        dispositioned_at: "2026-01-05T12:00:00Z",
      },
    });

    expect(await screen.findByText("Confirmed structuring pattern.")).toBeInTheDocument();
    expect(screen.queryByLabelText("Analyst ID")).not.toBeInTheDocument();
  });

  it("submits a disposition with the entered analyst, outcome, and rationale", async () => {
    vi.mocked(api.dispositionAlert).mockResolvedValue({
      disposition_id: 2,
      analyst_id: "test-analyst",
      outcome: "false_positive",
      rationale_notes: "Looks benign.",
      dispositioned_at: "2026-01-06T00:00:00Z",
    });
    const user = userEvent.setup();
    renderCaseDetail();

    await screen.findByLabelText("Analyst ID");
    await user.type(screen.getByLabelText("Analyst ID"), "test-analyst");
    await user.type(screen.getByLabelText("Rationale"), "Looks benign.");
    await user.click(screen.getByRole("button", { name: "Submit disposition" }));

    await waitFor(() =>
      expect(api.dispositionAlert).toHaveBeenCalledWith(42, {
        analyst_id: "test-analyst",
        outcome: "false_positive",
        rationale_notes: "Looks benign.",
      })
    );
  });
});
