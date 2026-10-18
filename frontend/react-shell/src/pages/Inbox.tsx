import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { InboxItem } from "@/components/gtex/InboxItem";
import { Empty, Loading, PageHeader } from "@/components/gtex/ui";
import { api } from "@/lib/api";

export default function InboxPage() {
  const [status, setStatus] = useState("open");
  const { data, isLoading } = useQuery({ queryKey: ["inbox", status], queryFn: async () => (await api.get("/owner/inbox", { params: { status } })).data.items });
  return (
    <div data-testid="inbox-page">
      <PageHeader eyebrow="Owner inbox" title="Messages & decisions" sub="Manager meetings, player unrest, regen breakthroughs, transfer bids, sponsor opportunities and competition invites."
        action={<div className="flex gap-1">{["open", "resolved", "all"].map((s) => <button key={s} data-testid={`inbox-filter-${s}`} onClick={() => setStatus(s)} className={`gx-btn ${status === s ? "gx-btn-primary" : "gx-btn-secondary"}`}>{s}</button>)}</div>} />
      {isLoading ? <Loading /> : (
        <div className="grid gap-3 lg:grid-cols-2">
          {(data || []).length === 0 && <Empty title="Nothing here" body="Advance the world day from the Control Center to generate new events." />}
          {(data || []).map((i: any) => <InboxItem key={i.id} item={i} />)}
        </div>
      )}
    </div>
  );
}
