import { useEffect } from "react";

import { fetchTicketById } from "../services/api";
import { useTicketStore } from "../store/ticketStore";

export function useTicketDetail(ticketId?: string) {
  const detail = useTicketStore((state) => state.selectedTicket);
  const loading = useTicketStore((state) => state.loadingDetail);
  const error = useTicketStore((state) => state.error);
  const setSelectedTicket = useTicketStore((state) => state.setSelectedTicket);
  const setLoadingDetail = useTicketStore((state) => state.setLoadingDetail);
  const setError = useTicketStore((state) => state.setError);
  const updateTicket = useTicketStore((state) => state.updateTicket);

  async function refresh() {
    if (!ticketId) {
      setSelectedTicket(null);
      return;
    }

    setLoadingDetail(true);
    setError(null);
    try {
      const nextDetail = await fetchTicketById(ticketId);
      setSelectedTicket(nextDetail);
      updateTicket({
        id: nextDetail.id,
        customer_email: nextDetail.customer_email,
        subject: nextDetail.subject,
        status: nextDetail.status,
        urgency_score: nextDetail.urgency_score,
        created_at: nextDetail.created_at,
      });
    } catch (refreshError) {
      setError(
        refreshError instanceof Error
          ? refreshError.message
          : "Failed to load ticket detail.",
      );
    } finally {
      setLoadingDetail(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, [ticketId]);

  return {
    detail,
    loading,
    error,
    refresh,
  };
}
