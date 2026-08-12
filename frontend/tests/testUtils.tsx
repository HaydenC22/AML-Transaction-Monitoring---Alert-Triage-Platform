import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactElement } from "react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

function newTestQueryClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
}

/** Wraps a page component that reads no route params. */
export function withProviders(ui: ReactElement) {
  return (
    <QueryClientProvider client={newTestQueryClient()}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>
  );
}

/** Wraps a page component that reads route params (e.g. useParams) via a real route match. */
export function withRoute(ui: ReactElement, path: string, route: string) {
  return (
    <QueryClientProvider client={newTestQueryClient()}>
      <MemoryRouter initialEntries={[route]}>
        <Routes>
          <Route path={path} element={ui} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}
