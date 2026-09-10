import { useEffect, useState } from "react";
import { NavLink, Link, useLocation } from "react-router-dom";
import { Menu, X } from "lucide-react";
import { api, mediaUrl } from "../lib/api";

const NAV = [
  { to: "/", label: "Home" },
  { to: "/our-story", label: "Our Story" },
  { to: "/menu", label: "Menu" },
  { to: "/buffet", label: "Buffet" },
  { to: "/gallery", label: "Gallery" },
  { to: "/banqueting", label: "Banqueting" },
  { to: "/catering", label: "Catering" },
  { to: "/offers", label: "Offers" },
  { to: "/membership", label: "Membership" },
  { to: "/contact", label: "Contact" },
  { to: "/admin", label: "Admin" },
];

export function BrandMark({ size = 34, color = "#C5A059" }) {
  // 22 radial petal/teardrops forming a mandala sun
  const petals = 22;
  const items = [];
  for (let i = 0; i < petals; i++) {
    const a = (360 / petals) * i;
    items.push(
      <g key={i} transform={`rotate(${a} 100 100)`}>
        <path
          d="M100 12 C 96 30 96 50 100 62 C 104 50 104 30 100 12 Z"
          fill="none"
          stroke={color}
          strokeWidth="3.2"
          strokeLinejoin="round"
        />
      </g>
    );
  }
  return (
    <svg viewBox="0 0 200 200" width={size} height={size} aria-hidden focusable="false">
      {items}
    </svg>
  );
}

export function Brand({ light = false }) {
  const gold = light ? "#B58A3E" : "#C5A059";
  const maroon = light ? "#4A0E17" : "#E8C88A"; // on dark header show wordmark in warm gold/cream
  const tag = light ? "rgba(74,14,23,0.7)" : "rgba(232,200,138,0.8)";
  return (
    <Link to="/" className="inline-flex items-center gap-3" data-testid="brand-logo">
      <BrandMark size={40} color={gold} />
      <span className="flex flex-col leading-none">
        <span
          className="font-serif-display"
          style={{ color: maroon, fontWeight: 700, fontSize: "1.35rem", letterSpacing: "0.01em" }}
        >
          Sip 'n' Dine
        </span>
        <span
          className="font-sans-brand"
          style={{ color: tag, fontSize: "0.52rem", letterSpacing: "0.32em", textTransform: "uppercase", marginTop: "3px" }}
        >
          Indian Fine Dining
        </span>
      </span>
    </Link>
  );
}

export function Header() {
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const loc = useLocation();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    onScroll();
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);
  useEffect(() => setOpen(false), [loc.pathname]);

  return (
    <>
    <header
      className="fixed top-0 left-0 right-0 z-50 transition-all duration-500"
      style={{
        background: scrolled ? "rgba(44,26,20,0.92)" : "rgba(44,26,20,0.55)",
        backdropFilter: "blur(16px)",
        borderBottom: "1px solid rgba(197,160,89,0.18)",
      }}
      data-testid="site-header"
    >
      <div className="max-w-[1400px] mx-auto px-6 md:px-10 flex items-center justify-between py-4">
        <Brand />
        <nav className="hidden lg:flex items-center gap-7" data-testid="desktop-nav">
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.to === "/"} className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`} data-testid={`nav-link-${n.label.toLowerCase().replace(/\s+/g, "-")}`}>
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="hidden lg:block">
          <Link to="/book-table" className="btn-gold" data-testid="header-book-table-btn">Book a Table</Link>
        </div>
        <button className="lg:hidden text-[color:var(--cream)]" onClick={() => setOpen(true)} data-testid="mobile-menu-open"><Menu size={22} /></button>
      </div>
    </header>

    {open && (
      <div
        className="fixed inset-0 lg:hidden"
        style={{ background: "#2C1A14", zIndex: 9999 }}
        data-testid="mobile-menu"
      >
        <div className="h-full w-full flex flex-col p-8 overflow-y-auto" style={{ background: "#2C1A14" }}>
          <div className="flex items-center justify-between">
            <Brand />
            <button className="text-[color:var(--cream)]" onClick={() => setOpen(false)} data-testid="mobile-menu-close"><X size={22} /></button>
          </div>
          <nav className="mt-14 flex flex-col gap-6">
            {NAV.map((n) => (
              <NavLink key={n.to} to={n.to} end={n.to === "/"} className={({ isActive }) => `nav-link text-lg ${isActive ? "active" : ""}`} data-testid={`mobile-nav-link-${n.label.toLowerCase().replace(/\s+/g, "-")}`}>
                {n.label}
              </NavLink>
            ))}
            <Link to="/book-table" className="btn-gold mt-6" data-testid="mobile-book-table-btn">Book a Table</Link>
          </nav>
        </div>
      </div>
    )}
    </>
  );
}

export function Footer() {
  const [s, setS] = useState(null);
  useEffect(() => { api.get("/settings").then((r) => setS(r.data)); }, []);
  if (!s) return null;
  return (
    <footer className="bg-[color:var(--wood)] text-[color:var(--cream)] pt-20 pb-10 px-6 md:px-10 relative overflow-hidden" data-testid="site-footer">
      <div className="max-w-[1400px] mx-auto grid md:grid-cols-4 gap-12">
        <div>
          <Brand />
          <p className="mt-6 text-sm leading-relaxed text-[color:var(--cream)]/70 font-serif-display italic">
            An unhurried table in Sector 7C — Awadhi, Punjabi and everything you loved growing up.
          </p>
        </div>
        <div>
          <div className="eyebrow mb-4">Visit</div>
          <p className="text-sm text-[color:var(--cream)]/80 leading-relaxed">{s.address}</p>
          <div className="eyebrow mt-6 mb-3">Hours</div>
          {s.hours?.map((h, i) => (
            <div key={i} className="text-xs text-[color:var(--cream)]/70 mb-1"><span className="text-[color:var(--gold)]">{h.day}</span> · {h.hours}</div>
          ))}
        </div>
        <div>
          <div className="eyebrow mb-4">Reach</div>
          {s.phones?.map((p, i) => (
            <a key={i} href={`tel:${p.replace(/\s/g, "")}`} className="block text-sm text-[color:var(--cream)]/80 hover:text-[color:var(--gold)] transition mb-1" data-testid={`footer-phone-${i}`}>{p}</a>
          ))}
          <a href={`mailto:${s.email}`} className="block text-sm text-[color:var(--cream)]/80 hover:text-[color:var(--gold)] mt-2" data-testid="footer-email">{s.email}</a>
          <div className="eyebrow mt-6 mb-3">Social</div>
          <div className="flex gap-4">
            {s.social?.instagram && <a href={s.social.instagram} className="text-[color:var(--gold)] hover:text-[color:var(--gold-bright)]" target="_blank" rel="noreferrer" data-testid="footer-instagram"><i className="fa-brands fa-instagram text-lg" /></a>}
            {s.social?.facebook && <a href={s.social.facebook} className="text-[color:var(--gold)] hover:text-[color:var(--gold-bright)]" target="_blank" rel="noreferrer" data-testid="footer-facebook"><i className="fa-brands fa-facebook text-lg" /></a>}
          </div>
        </div>
        <div>
          <div className="eyebrow mb-4">The Table</div>
          <Link to="/book-table" className="btn-outline-gold text-xs" data-testid="footer-book-btn">Book a Table</Link>
          <div className="eyebrow mt-8 mb-3">Owner Access</div>
          <Link to="/admin" className="text-xs text-[color:var(--cream)]/60 hover:text-[color:var(--gold)] tracking-wider uppercase" data-testid="footer-admin-link">Admin Sign-in</Link>
        </div>
      </div>
      <div className="max-w-[1400px] mx-auto mt-14 pt-8 border-t border-[color:var(--gold)]/15 flex flex-col md:flex-row justify-between items-center gap-4 text-xs text-[color:var(--cream)]/50">
        <div>© {new Date().getFullYear()} Sip 'n' Dine · Sector 7C · Chandigarh</div>
        <div className="font-script text-[color:var(--gold)]/70 text-lg">Owners also eat here.</div>
      </div>
    </footer>
  );
}

export function PageHero({ eyebrow, title, image, intro }) {
  return (
    <section className="relative h-[65vh] min-h-[440px] w-full flex items-end overflow-hidden" data-testid="page-hero">
      <img src={mediaUrl(image)} alt="" className="absolute inset-0 w-full h-full object-cover" />
      <div className="absolute inset-0" style={{ background: "linear-gradient(to top, rgba(44,26,20,0.85), rgba(44,26,20,0.35) 55%, rgba(44,26,20,0.55))" }} />
      <div className="relative z-10 w-full max-w-[1400px] mx-auto px-6 md:px-10 pb-16 text-[color:var(--cream)] fade-up">
        {eyebrow && <div className="eyebrow mb-4">{eyebrow}</div>}
        <h1 className="font-serif-display text-4xl sm:text-5xl lg:text-7xl leading-none max-w-4xl">{title}</h1>
        {intro && <p className="mt-6 font-serif-display italic text-lg md:text-xl max-w-2xl text-[color:var(--cream)]/85">{intro}</p>}
      </div>
    </section>
  );
}

export function Diamond() { return <div className="divider-diamond my-12"><i className="fa-solid fa-diamond text-[10px]" /></div>; }
