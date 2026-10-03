function BookingsManager() {
  const [items, setItems] = useState([]);

  const load = () =>
    api.get("/admin/bookings").then((r) => setItems(r.data));

  useEffect(() => {
    load();
  }, []);

  const setStatus = async (b, status) => {
    await api.put(`/admin/bookings/${b.id}`, { status });
    load();
    toast.success(`Marked ${status}`);
  };

  const del = async (b) => {
    if (!window.confirm("Delete booking?")) return;
    await api.delete(`/admin/bookings/${b.id}`);
    load();
  };

  return (
    <div data-testid="bookings-manager">
      <div className="eyebrow mb-4">
        {items.length} reservations
      </div>

      <div className="grid gap-3">
        {items.map((b) => (
          <div
            key={b.id}
            className="border p-4 flex flex-wrap items-center gap-4 justify-between bg-[color:var(--cream-muted)]"
            data-testid={`booking-row-${b.id}`}
          >
            <div>
              <div className="font-serif-display text-xl">
                {b.name} · Party of {b.party_size}
              </div>

              <div className="text-xs uppercase tracking-widest text-[color:var(--wood)]/60">
                {b.date} · {b.time} · {b.phone}
              </div>

              {b.notes && (
                <div className="text-sm mt-1 italic">
                  {b.notes}
                </div>
              )}
            </div>

            <div className="flex gap-2 items-center">
              <span
                className={`px-2 py-1 text-xs uppercase ${
                  b.status === "confirmed"
                    ? "bg-green-700 text-white"
                    : b.status === "cancelled"
                    ? "bg-red-700 text-white"
                    : "bg-[color:var(--gold)] text-[color:var(--wood)]"
                }`}
              >
                {b.status}
              </span>

              <button
                className="btn-outline-gold text-xs px-3 py-1"
                onClick={() => setStatus(b, "confirmed")}
              >
                Confirm
              </button>

              <button
                className="btn-outline-gold text-xs px-3 py-1"
                onClick={() => setStatus(b, "cancelled")}
              >
                Cancel
              </button>

              <button
                className="text-xs text-red-700 underline"
                onClick={() => del(b)}
              >
                Delete
              </button>
            </div>
          </div>
        ))}

        {items.length === 0 && (
          <div className="italic text-[color:var(--wood)]/50">
            No reservations yet.
          </div>
        )}
      </div>
    </div>
  );
}
