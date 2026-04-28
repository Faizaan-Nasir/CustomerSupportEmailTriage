import { useEffect } from "react";

import { fetchTickets } from "../services/api";
import { useTicketStore } from "../store/ticketStore";

export function useTickets() {
  const tickets = useTicketStore((state) => state.tickets);
  const loading = useTicketStore((state) => state.loadingTickets);
  const error = useTicketStore((state) => state.error);
  const setTickets = useTicketStore((state) => state.setTickets);
  const setLoadingTickets = useTicketStore((state) => state.setLoadingTickets);
  const setError = useTicketStore((state) => state.setError);

  async function refresh() {
    setLoadingTickets(true);
    setError(null);
    try {
      const nextTickets = await fetchTickets();
      setTickets(nextTickets);
    } catch (refreshError) {
      setError(
        refreshError instanceof Error ? refreshError.message : "Failed to load tickets.",
      );
    } finally {
      setLoadingTickets(false);
    }
  }

  useEffect(() => {
    if (tickets.length === 0) {
      void refresh();
    }
  }, []);

  return {
    tickets,
    loading,
    error,
    refresh,
  };
}
