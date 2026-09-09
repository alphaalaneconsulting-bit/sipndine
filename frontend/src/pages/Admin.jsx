import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, mediaUrl } from "../lib/api";
import { useAuth } from "../lib/auth";
import { toast } from "sonner";

function Login() {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [pwd, setPwd] = useState("");
  const [err, setErr] = useState("");
  const submit = async (e) => {
    e.preventDefault(); setErr("");
    try { await login(email, pwd); } catch { setErr("Invalid credentials"); }
  };
  return (
    <div className="min-h-screen flex items-center justify-center bg-[color:var(--wood)] p-6" data-testid="admin-login">
      <form onSubmit={submit} className="w-full max-w-md bg-[color:var(--cream)] p-10 border border-[color:var(--gold)]/40">
        <div className="text-center mb-8">
          <div className="font-script text-4xl text-[color:var(--maroon)]">Sip 'n' Dine</div>
          <div className="eyebrow mt-2">Owner Access</div>
        </div>
        <label className="eyebrow block mb-2">Email</label>
        <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className="w-full p-3 border border-[color:var(--gold)]/40 bg-transparent mb-4" data-testid="admin-login-email-input" />
        <label className="eyebrow block mb-2">Password</label>
        <input type="password" required value={pwd} onChange={(e) => setPwd(e.target.value)} className="w-full p-3 border border-[color:var(--gold)]/40 bg-transparent mb-6" data-testid="admin-login-password-input" />
        {err && <div className="text-sm text-[color:var(--maroon)] mb-4" data-testid="admin-login-error">{err}</div>}
        <button className="btn-primary w-full justify-center" type="submit" data-testid="admin-login-submit">Sign In</button>
      </form>
    </div>
  );
}

const PAGE_SLUGS = ["home", "our-story", "menu", "buffet", "gallery", "banqueting", "catering", "offers", "membership", "book-table", "contact"];

function ContentEditor() {
  const [slug, setSlug] = useState("home");
  const [c, setC] = useState(null);
  useEffect(() => { api.get(`/content/${slug}`).then((r) => setC(r.data)); }, [slug]);
  const save = async () => { await api.put(`/content/${slug}`, c); toast.success("Saved"); };
  if (!c) return null;
  return (
    <div className="space-y-4" data-testid="content-editor">
      <div className="flex flex-wrap gap-2 border-b pb-3">
        {PAGE_SLUGS.map((s) => <button key={s} onClick={() => setSlug(s)} className={`px-3 py-1 text-xs uppercase tracking-widest border ${slug === s ? "bg-[color:var(--maroon)] text-white border-[color:var(--maroon)]" : "border-[color:var(--gold)]/40"}`} data-testid={`content-slug-${s}`}>{s}</button>)}
      </div>
      <label className="eyebrow">Eyebrow</label>
      <input className="w-full p-2 border" value={c.eyebrow || ""} onChange={(e) => setC({ ...c, eyebrow: e.target.value })} data-testid="content-eyebrow" />
      <label className="eyebrow">Title</label>
      <input className="w-full p-2 border" value={c.title || ""} onChange={(e) => setC({ ...c, title: e.target.value })} data-testid="content-title" />
      <label className="eyebrow">Hero Image URL</label>
      <input className="w-full p-2 border" value={c.hero_image || ""} onChange={(e) => setC({ ...c, hero_image: e.target.value })} data-testid="content-hero" />
      <label className="eyebrow">Intro</label>
      <textarea rows="3" className="w-full p-2 border" value={c.intro || ""} onChange={(e) => setC({ ...c, intro: e.target.value })} data-testid="content-intro" />
      <label className="eyebrow">Body HTML (rich text)</label>
      <textarea rows="10" className="w-full p-2 border font-mono text-xs" value={c.body_html || ""} onChange={(e) => setC({ ...c, body_html: e.target.value })} data-testid="content-body" />
      <button className="btn-primary" onClick={save} data-testid="content-save">Save Page</button>
    </div>
  );
}

function BookingsManager() {
  const [items, setItems] = useState([]);
  const load = () => api.get("/admin/bookings").then((r) => setItems(r.data));
  useEffect(() => { load(); }, []);
  const setStatus = async (b, status) => { await api.put(`/admin/bookings/${b.id}`, { status }); load(); toast.success(`Marked ${status}`); };
  const del = async (b) => { if (!window.confirm("Delete booking?")) return; await api.delete(`/admin/bookings/${b.id}`); load(); };
  return (
    <div data-testid="bookings-manager">
      <div className="eyebrow mb-4">{items.length} reservations</div>
      <div className="grid gap-3">
        {items.map((b) => (
          <div key={b.id} className="border p-4 flex flex-wrap items-center gap-4 justify-between bg-[color:var(--cream-muted)]" data-testid={`booking-row-${b.id}`}>
            <div>
              <div className="font-serif-display text-xl">{b.name} · Party of {b.party_size}</div>
              <div className="text-xs uppercase tracking-widest text-[color:var(--wood)]/60">{b.date} · {b.time} · {b.phone}</div>
              {b.notes && <div className="text-sm mt-1 italic">{b.notes}</div>}
            </div>
            <div className="flex gap-2 items-center">
              <span className={`px-2 py-1 text-xs uppercase ${b.status === "confirmed" ? "bg-green-700 text-white" : b.status === "cancelled" ? "bg-red-700 text-white" : "bg-[color:var(--gold)] text-[color:var(--wood)]"}`}>{b.status}</span>
              <button className="btn-outline-gold text-xs px-3 py-1" onClick={() => setStatus(b, "confirmed")} data-testid={`booking-confirm-${b.id}`}>Confirm</button>
              <button className="btn-outline-gold text-xs px-3 py-1" onClick={() => setStatus(b, "cancelled")} data-testid={`booking-cancel-${b.id}`}>Cancel</button>
              <button className="text-xs text-red-700 underline" onClick={() => del(b)} data-testid={`booking-delete-${b.id}`}>Delete</button>
            </div>
          </div>
        ))}
        {items.length === 0 && <div className="italic text-[color:var(--wood)]/50">No reservations yet.</div>}
      </div>
    </div>
  );
}

function MenuManager() {
  const [items, setItems] = useState([]);
  const [editing, setEditing] = useState(null);
  const [genId, setGenId] = useState(null);
  const load = () => api.get("/menu").then((r) => setItems(r.data));
  useEffect(() => { load(); }, []);
  const save = async () => {
    if (editing.id && items.find((i) => i.id === editing.id)) await api.put(`/admin/menu/${editing.id}`, editing);
    else await api.post("/admin/menu", editing);
    setEditing(null); load(); toast.success("Saved");
  };
  const del = async (i) => { if (!window.confirm("Delete dish?")) return; await api.delete(`/admin/menu/${i.id}`); load(); };
  const gen = async (i) => {
    setGenId(i.id);
    try {
      const r = await api.post("/admin/generate-image", { prompt: `${i.name} — ${i.description}`, item_id: i.id });
      toast.success("Image generated"); load();
    } catch { toast.error("Generation failed"); }
    setGenId(null);
  };
  return (
    <div data-testid="menu-manager">
      <div className="flex justify-between items-center mb-4">
        <div className="eyebrow">{items.length} dishes</div>
        <button className="btn-primary" onClick={() => setEditing({ name: "", category: "Starters", description: "", price: 0, veg: true, signature: false, image_url: "", order: items.length })} data-testid="menu-add-btn">+ Add Dish</button>
      </div>
      <div className="grid md:grid-cols-2 gap-3">
        {items.map((i) => (
          <div key={i.id} className="border p-3 flex gap-3 items-center bg-white" data-testid={`menu-mgr-row-${i.id}`}>
            {i.image_url ? <img src={mediaUrl(i.image_url)} className="w-16 h-16 object-cover" alt="" /> : <div className="w-16 h-16 bg-[color:var(--wood)]/10" />}
            <div className="flex-1 min-w-0">
              <div className="font-serif-display truncate">{i.name}</div>
              <div className="text-xs text-[color:var(--wood)]/60">{i.category} · ₹{i.price}</div>
            </div>
            <div className="flex flex-col gap-1">
              <button className="text-xs underline" onClick={() => setEditing(i)} data-testid={`menu-edit-${i.id}`}>Edit</button>
              <button className="text-xs underline text-[color:var(--maroon)]" onClick={() => gen(i)} disabled={genId === i.id} data-testid={`menu-gen-${i.id}`}>{genId === i.id ? "Generating…" : "AI Photo"}</button>
              <button className="text-xs text-red-700 underline" onClick={() => del(i)} data-testid={`menu-del-${i.id}`}>Delete</button>
            </div>
          </div>
        ))}
      </div>
      {editing && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-6" onClick={() => setEditing(null)}>
          <div className="bg-white p-6 max-w-lg w-full space-y-3" onClick={(e) => e.stopPropagation()} data-testid="menu-edit-modal">
            <div className="font-serif-display text-2xl">{editing.id && items.find(i => i.id === editing.id) ? "Edit Dish" : "New Dish"}</div>
            <input placeholder="Name" className="w-full p-2 border" value={editing.name} onChange={(e) => setEditing({ ...editing, name: e.target.value })} data-testid="menu-edit-name" />
            <input placeholder="Category" className="w-full p-2 border" value={editing.category} onChange={(e) => setEditing({ ...editing, category: e.target.value })} data-testid="menu-edit-category" />
            <textarea placeholder="Description" rows="2" className="w-full p-2 border" value={editing.description} onChange={(e) => setEditing({ ...editing, description: e.target.value })} data-testid="menu-edit-desc" />
            <input type="number" placeholder="Price" className="w-full p-2 border" value={editing.price || 0} onChange={(e) => setEditing({ ...editing, price: parseFloat(e.target.value) })} data-testid="menu-edit-price" />
            <input placeholder="Image URL" className="w-full p-2 border" value={editing.image_url || ""} onChange={(e) => setEditing({ ...editing, image_url: e.target.value })} />
            <label className="flex gap-2 text-sm"><input type="checkbox" checked={editing.veg} onChange={(e) => setEditing({ ...editing, veg: e.target.checked })} /> Vegetarian</label>
            <label className="flex gap-2 text-sm"><input type="checkbox" checked={editing.signature} onChange={(e) => setEditing({ ...editing, signature: e.target.checked })} /> Signature</label>
            <div className="flex gap-2 justify-end">
              <button className="btn-outline-gold" onClick={() => setEditing(null)}>Cancel</button>
              <button className="btn-primary" onClick={save} data-testid="menu-edit-save">Save</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function SettingsPanel() {
  const [s, setS] = useState(null);
  useEffect(() => { api.get("/settings").then((r) => setS(r.data)); }, []);
  if (!s) return null;
  const save = async () => { await api.put("/settings", s); toast.success("Settings saved"); };
  return (
    <div className="space-y-3" data-testid="settings-panel">
      <label className="eyebrow">Address</label>
      <textarea rows="2" className="w-full p-2 border" value={s.address} onChange={(e) => setS({ ...s, address: e.target.value })} data-testid="settings-address" />
      <label className="eyebrow">Phones (comma separated)</label>
      <input className="w-full p-2 border" value={s.phones.join(", ")} onChange={(e) => setS({ ...s, phones: e.target.value.split(",").map(x => x.trim()).filter(Boolean) })} data-testid="settings-phones" />
      <label className="eyebrow">Email</label>
      <input className="w-full p-2 border" value={s.email} onChange={(e) => setS({ ...s, email: e.target.value })} data-testid="settings-email" />
      <label className="eyebrow">Logo URL (upload asset then paste)</label>
      <input className="w-full p-2 border" value={s.logo_url || ""} onChange={(e) => setS({ ...s, logo_url: e.target.value })} />
      <label className="eyebrow">Map Embed URL</label>
      <input className="w-full p-2 border" value={s.map_embed_url || ""} onChange={(e) => setS({ ...s, map_embed_url: e.target.value })} data-testid="settings-map" />
      <div className="eyebrow mt-4">Hours</div>
      {s.hours.map((h, i) => (
        <div key={i} className="grid grid-cols-2 gap-2">
          <input className="p-2 border" value={h.day} onChange={(e) => { const arr = [...s.hours]; arr[i] = { ...h, day: e.target.value }; setS({ ...s, hours: arr }); }} />
          <input className="p-2 border" value={h.hours} onChange={(e) => { const arr = [...s.hours]; arr[i] = { ...h, hours: e.target.value }; setS({ ...s, hours: arr }); }} />
        </div>
      ))}
      <button className="btn-outline-gold text-xs" onClick={() => setS({ ...s, hours: [...s.hours, { day: "", hours: "" }] })}>+ Add Row</button>
      <div className="eyebrow mt-4">Social</div>
      <input placeholder="Instagram URL" className="w-full p-2 border" value={s.social?.instagram || ""} onChange={(e) => setS({ ...s, social: { ...s.social, instagram: e.target.value } })} />
      <input placeholder="Facebook URL" className="w-full p-2 border" value={s.social?.facebook || ""} onChange={(e) => setS({ ...s, social: { ...s.social, facebook: e.target.value } })} />
      <button className="btn-primary" onClick={save} data-testid="settings-save">Save Settings</button>
    </div>
  );
}

function GenericCRUD({ endpoint, fields, title, testid, defaults }) {
  const [items, setItems] = useState([]);
  const [edit, setEdit] = useState(null);
  const load = () => api.get(`/${endpoint}`).then((r) => setItems(r.data));
  useEffect(() => { load(); }, []);
  const save = async () => {
    if (edit.id && items.find((i) => i.id === edit.id)) await api.put(`/admin/${endpoint}/${edit.id}`, edit);
    else await api.post(`/admin/${endpoint}`, edit);
    setEdit(null); load(); toast.success("Saved");
  };
  const del = async (i) => { if (!window.confirm("Delete?")) return; await api.delete(`/admin/${endpoint}/${i.id}`); load(); };
  return (
    <div data-testid={testid}>
      <div className="flex justify-between mb-3">
        <div className="eyebrow">{items.length} {title}</div>
        <button className="btn-primary" onClick={() => setEdit({ ...defaults })} data-testid={`${testid}-add`}>+ Add</button>
      </div>
      <div className="grid gap-2">
        {items.map((i) => (
          <div key={i.id} className="border p-3 flex justify-between items-center bg-white">
            <div className="text-sm">{fields.map((f) => <span key={f.k} className="mr-3"><b>{f.label}:</b> {String(i[f.k] ?? "")}</span>)}</div>
            <div className="flex gap-2"><button className="text-xs underline" onClick={() => setEdit(i)}>Edit</button><button className="text-xs text-red-700 underline" onClick={() => del(i)}>Delete</button></div>
          </div>
        ))}
      </div>
      {edit && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-6" onClick={() => setEdit(null)}>
          <div className="bg-white p-6 max-w-lg w-full space-y-3 max-h-[85vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="font-serif-display text-2xl">{title}</div>
            {fields.map((f) => f.type === "textarea" ? (
              <div key={f.k}><label className="eyebrow">{f.label}</label><textarea rows="3" className="w-full p-2 border" value={edit[f.k] || ""} onChange={(e) => setEdit({ ...edit, [f.k]: e.target.value })} /></div>
            ) : f.type === "list" ? (
              <div key={f.k}><label className="eyebrow">{f.label} (one per line)</label><textarea rows="4" className="w-full p-2 border" value={(edit[f.k] || []).join("\n")} onChange={(e) => setEdit({ ...edit, [f.k]: e.target.value.split("\n").filter(Boolean) })} /></div>
            ) : f.type === "bool" ? (
              <label key={f.k} className="flex gap-2"><input type="checkbox" checked={!!edit[f.k]} onChange={(e) => setEdit({ ...edit, [f.k]: e.target.checked })} /> {f.label}</label>
            ) : (
              <div key={f.k}><label className="eyebrow">{f.label}</label><input type={f.type || "text"} className="w-full p-2 border" value={edit[f.k] || ""} onChange={(e) => setEdit({ ...edit, [f.k]: f.type === "number" ? parseInt(e.target.value) : e.target.value })} /></div>
            ))}
            <div className="flex gap-2 justify-end"><button className="btn-outline-gold" onClick={() => setEdit(null)}>Cancel</button><button className="btn-primary" onClick={save}>Save</button></div>
          </div>
        </div>
      )}
    </div>
  );
}

const TABS = [
  { key: "bookings", label: "Reservations" },
  { key: "content", label: "Page Content" },
  { key: "menu", label: "Menu" },
  { key: "settings", label: "Global Settings" },
  { key: "recognition", label: "Why Chandigarh" },
  { key: "offers", label: "Offers" },
  { key: "membership", label: "Membership" },
  { key: "gallery", label: "Gallery" },
  { key: "enquiries", label: "Enquiries" },
  { key: "waitlist", label: "Waitlist" },
];

function Dashboard() {
  const [tab, setTab] = useState("bookings");
  const { logout, user } = useAuth();
  const nav = useNavigate();
  const doLogout = () => { logout(); nav("/"); };
  return (
    <div className="min-h-screen bg-[color:var(--cream-muted)]" data-testid="admin-dashboard">
      <header className="bg-[color:var(--wood)] text-[color:var(--cream)] p-6 flex justify-between items-center">
        <div>
          <div className="font-script text-3xl text-[color:var(--gold)]">Sip 'n' Dine</div>
          <div className="text-xs uppercase tracking-widest">Owner Dashboard · {user?.email}</div>
        </div>
        <button className="btn-outline-gold text-xs" onClick={doLogout} data-testid="admin-logout">Sign Out</button>
      </header>
      <div className="grid md:grid-cols-[220px_1fr] gap-6 p-6 max-w-[1400px] mx-auto">
        <nav className="space-y-1">
          {TABS.map((t) => <button key={t.key} onClick={() => setTab(t.key)} className={`block w-full text-left px-3 py-2 text-sm uppercase tracking-widest border-l-4 ${tab === t.key ? "border-[color:var(--maroon)] bg-white font-semibold" : "border-transparent hover:bg-white/50"}`} data-testid={`admin-tab-${t.key}`}>{t.label}</button>)}
        </nav>
        <main className="bg-white p-6 border">
          {tab === "bookings" && <BookingsManager />}
          {tab === "content" && <ContentEditor />}
          {tab === "menu" && <MenuManager />}
          {tab === "settings" && <SettingsPanel />}
          {tab === "recognition" && <GenericCRUD endpoint="recognition" testid="recognition-crud" title="Recognition Entry"
            fields={[{ k: "platform", label: "Platform" }, { k: "rating", label: "Rating" }, { k: "quote", label: "Quote", type: "textarea" }, { k: "icon", label: "Icon (star/award/heart)" }, { k: "order", label: "Order", type: "number" }]}
            defaults={{ platform: "", rating: "", quote: "", icon: "star", order: 0 }} />}
          {tab === "offers" && <GenericCRUD endpoint="offers" testid="offers-crud" title="Offer"
            fields={[{ k: "title", label: "Title" }, { k: "subtitle", label: "Subtitle" }, { k: "description", label: "Description", type: "textarea" }, { k: "valid_till", label: "Valid Till" }, { k: "image_url", label: "Image URL" }, { k: "active", label: "Active", type: "bool" }, { k: "order", label: "Order", type: "number" }]}
            defaults={{ title: "", subtitle: "", description: "", valid_till: "", image_url: "", active: true, order: 0 }} />}
          {tab === "membership" && <GenericCRUD endpoint="membership" testid="membership-crud" title="Tier"
            fields={[{ k: "name", label: "Name" }, { k: "price", label: "Price" }, { k: "tagline", label: "Tagline" }, { k: "benefits", label: "Benefits", type: "list" }, { k: "highlighted", label: "Highlighted", type: "bool" }, { k: "order", label: "Order", type: "number" }]}
            defaults={{ name: "", price: "", tagline: "", benefits: [], highlighted: false, order: 0 }} />}
          {tab === "gallery" && <GenericCRUD endpoint="gallery" testid="gallery-crud" title="Photo"
            fields={[{ k: "url", label: "URL" }, { k: "caption", label: "Caption" }, { k: "order", label: "Order", type: "number" }]}
            defaults={{ url: "", caption: "", order: 0 }} />}
          {tab === "enquiries" && <EnquiriesPanel />}
          {tab === "waitlist" && <WaitlistPanel />}
        </main>
      </div>
    </div>
  );
}

function EnquiriesPanel() {
  const [items, setItems] = useState([]);
  const load = () => api.get("/admin/enquiries").then((r) => setItems(r.data));
  useEffect(() => { load(); }, []);
  return (
    <div data-testid="enquiries-panel">
      <div className="eyebrow mb-4">{items.length} enquiries</div>
      {items.map((e) => (
        <div key={e.id} className="border p-4 mb-3 bg-[color:var(--cream-muted)]">
          <div className="flex justify-between"><b>{e.name}</b><span className="eyebrow text-[color:var(--maroon)]">{e.kind}</span></div>
          <div className="text-xs uppercase tracking-widest text-[color:var(--wood)]/60">{e.phone} · {e.email} · {e.date} · {e.guests} guests</div>
          <p className="mt-2 italic">{e.message}</p>
        </div>
      ))}
    </div>
  );
}
function WaitlistPanel() {
  const [items, setItems] = useState([]);
  useEffect(() => { api.get("/admin/waitlist").then((r) => setItems(r.data)); }, []);
  return <div data-testid="waitlist-panel"><div className="eyebrow mb-4">{items.length} on waitlist</div><ul className="space-y-1 text-sm">{items.map((i) => <li key={i.id}>{i.email} <span className="text-xs text-[color:var(--wood)]/50">· {i.created_at?.slice(0, 10)}</span></li>)}</ul></div>;
}

export default function Admin() {
  const { user, ready } = useAuth();
  if (!ready) return <div className="min-h-screen flex items-center justify-center bg-[color:var(--wood)] text-[color:var(--cream)]">Loading…</div>;
  return user ? <Dashboard /> : <Login />;
}
