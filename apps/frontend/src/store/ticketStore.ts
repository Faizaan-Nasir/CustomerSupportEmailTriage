import { create } from "zustand";

import type { TicketDetail, TicketListItem } from "../types/ticket";

interface TicketStoreState {
  tickets: TicketListItem[];
  selectedTicket: TicketDetail | null;
  loadingTickets: boolean;
  loadingDetail: boolean;
  error: string | null;
  setTickets: (tickets: TicketListItem[]) => void;
  setSelectedTicket: (ticket: TicketDetail | null) => void;
  setLoadingTickets: (loading: boolean) => void;
  setLoadingDetail: (loading: boolean) => void;
  setError: (error: string | null) => void;
  updateTicket: (ticket: Partial<TicketListItem> & { id: string }) => void;
}

export const useTicketStore = create<TicketStoreState>((set) => ({
  tickets: [],
  selectedTicket: null,
  loadingTickets: false,
  loadingDetail: false,
  error: null,
  setTickets: (tickets) => set({ tickets }),
  setSelectedTicket: (selectedTicket) => set({ selectedTicket }),
  setLoadingTickets: (loadingTickets) => set({ loadingTickets }),
  setLoadingDetail: (loadingDetail) => set({ loadingDetail }),
  setError: (error) => set({ error }),
  updateTicket: (ticket) =>
    set((state) => ({
      tickets: state.tickets.map((current) =>
        current.id === ticket.id ? { ...current, ...ticket } : current,
      ),
    })),
}));
