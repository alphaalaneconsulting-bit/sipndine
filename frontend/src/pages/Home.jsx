import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, mediaUrl } from "../lib/api";
import { PageHero, Diamond } from "../components/Layout";

function useContent(slug) {
  const [c, setC] = useState(null);
  useEffect(() => { api.get(`/content/${slug}`).then((r) => setC(r.data)); }, [slug]);
  return c;
}

export default function Home() {
  const c = useContent("home");
  const [dishes, setDishes] = useState([]);
  const [recognition, setRecognition] = useState([]);

  useEffect(() => {
    api.get("/menu").then((r) => setDishes(r.data.filter((d) => d.signature).slice(0, 4)));
    api.get("/recognition").then((r) => setRecognition(r.data));
  }, []);

  const tiles = [
    { to: "/menu", label: "The Menu", img: "/restaurant/image7.jpeg" },
    { to: "/buffet", label: "Buffet", img: "/restaurant/image3.jpeg" },
    { to: "/banqueting", label: "Private Dining", img: "/restaurant/image5.jpeg" },
    { to: "/catering", label: "Catering", img: "/restaurant/image4.jpeg" },
    { to: "/offers", label: "Offers", img: "/restaurant/image6.jpeg" },
    { to: "/membership", label: "Membership", img: "/restaurant/image1.jpeg" },
  ];

  return (
    <div data-testid="home-page">
      {/* Hero */}
      <section className="relative h-screen min-h-[600px] w-full overflow-hidden" data-testid="home-hero">
        <img src={mediaUrl(c?.hero_image || "/restaurant/image1.jpeg")} alt="Sip 'n' Dine dining room" className="absolute inset-0 w-full h-full object-cover" />
        <div className="absolute inset-0" style={{ background: "linear-gradient(to bottom, rgba(44,26,20,0.55), rgba(44,26,20,0.35) 40%, rgba(44,26,20,0.85))" }} />
        <div className="relative z-10 h-full flex flex-col justify-center max-w-[1400px] mx-auto px-6 md:px-10 text-[color:var(--cream)]">
          <div className="fade-up eyebrow mb-6" style={{ color: "var(--gold)" }}>{c?.eyebrow || "Chandigarh · Sector 7C"}</div>
          <h1 className="fade-up fade-up-delay-1 font-serif-display text-5xl md:text-7xl lg:text-8xl leading-[1.02] max-w-4xl">{c?.title || "An unhurried table"}</h1>
          <p className="fade-up fade-up-delay-2 mt-8 font-serif-display italic text-xl md:text-2xl max-w-2xl text-[color:var(--cream)]/85">{c?.intro}</p>
          <div className="fade-up fade-up-delay-3 mt-10 flex flex-wrap gap-4">
            <Link to="/book-table" className="btn-gold" data-testid="hero-book-table-btn">Book a Table</Link>
            <Link to="/menu" className="btn-outline-gold" data-testid="hero-view-menu-btn">View Menu</Link>
          </div>
        </div>
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 text-[color:var(--gold)] text-xs tracking-[0.3em] uppercase animate-pulse">Scroll</div>
      </section>

      {/* Our Story teaser */}
      <section className="section bg-[color:var(--cream)]" data-testid="home-story-teaser">
        <div className="container-narrow grid md:grid-cols-2 gap-16 items-center">
          <div className="hover-zoom order-2 md:order-1">
            <img src="/restaurant/image5.jpeg" alt="Sip 'n' Dine dining" className="w-full h-[520px] object-cover" />
          </div>
          <div className="order-1 md:order-2">
            <div className="eyebrow mb-5">Our Story</div>
            <h2 className="font-serif-display text-4xl md:text-5xl leading-tight text-[color:var(--wood)]">A family table that grew into a neighbourhood.</h2>
            <p className="mt-8 font-serif-display text-lg italic leading-relaxed text-[color:var(--wood)]/75">
              Two decades on Madhya Marg. Recipes older than the room. Dal simmered for a full day, biryanis rested overnight, and a wall sign that reads — <em>Owners also eat here.</em>
            </p>
            <Link to="/our-story" className="mt-8 inline-block btn-outline-gold" data-testid="home-read-story-btn">Read Our Story</Link>
          </div>
        </div>
      </section>

      {/* Why Chandigarh Loves Us */}
      <section className="section bg-[color:var(--wood)] text-[color:var(--cream)] relative grain" data-testid="home-recognition">
        <div className="container-narrow relative">
          <div className="text-center">
            <div className="eyebrow mb-4">Recognition</div>
            <h2 className="font-serif-display text-4xl md:text-5xl">Why Chandigarh <span className="font-script text-[color:var(--gold)] text-6xl md:text-7xl">loves</span> us</h2>
          </div>
          <Diamond />
          <div className="grid md:grid-cols-3 lg:grid-cols-5 gap-6 mt-10">
            {recognition.map((r) => (
              <div key={r.id} className="border border-[color:var(--gold)]/25 p-8 text-center hover:border-[color:var(--gold)]/70 transition-all duration-500 hover:-translate-y-1" data-testid={`recognition-card-${r.platform.toLowerCase().replace(/\s+/g, "-")}`}>
                <div className="text-[color:var(--gold)] text-3xl mb-3">
                  <i className={`fa-solid fa-${r.icon === "award" ? "award" : r.icon === "heart" ? "heart" : "star"}`} />
                </div>
                <div className="font-serif-display text-2xl">{r.rating}</div>
                <div className="eyebrow mt-3 text-[color:var(--gold)]/90">{r.platform}</div>
                <p className="mt-4 text-xs italic text-[color:var(--cream)]/70 leading-relaxed">{r.quote}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Signature Dishes */}
      <section className="section bg-[color:var(--cream-muted)]" data-testid="home-signature-dishes">
        <div className="container-narrow">
          <div className="flex items-end justify-between flex-wrap gap-4">
            <div>
              <div className="eyebrow mb-3">On the Table Tonight</div>
              <h2 className="font-serif-display text-4xl md:text-5xl text-[color:var(--wood)]">Signature dishes</h2>
            </div>
            <Link to="/menu" className="btn-outline-gold" data-testid="home-view-full-menu-btn">Full Menu →</Link>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6 mt-12">
            {dishes.length === 0 ? Array(4).fill(0).map((_, i) => (
              <div key={i} className="aspect-[3/4] bg-[color:var(--wood)]/5 border border-[color:var(--gold)]/20 flex items-center justify-center">
                <span className="eyebrow text-[color:var(--wood)]/40">Coming Soon</span>
              </div>
            )) : dishes.map((d) => (
              <Link to="/menu" key={d.id} className="group card-warm hover-zoom" data-testid={`signature-dish-${d.id}`}>
                <div className="aspect-[4/5] overflow-hidden bg-[color:var(--wood)]/10">
                  {d.image_url ? <img src={mediaUrl(d.image_url)} alt={d.name} className="w-full h-full object-cover" /> : <div className="w-full h-full flex items-center justify-center eyebrow text-[color:var(--wood)]/40">Coming Soon</div>}
                </div>
                <div className="p-5">
                  <div className="flex items-center gap-2"><span className={d.veg ? "tag-veg" : "tag-nonveg"} /><span className="eyebrow text-[color:var(--gold)]">{d.category}</span></div>
                  <h3 className="font-serif-display text-2xl mt-2 text-[color:var(--wood)]">{d.name}</h3>
                  <p className="text-sm text-[color:var(--wood)]/60 mt-2 line-clamp-2 font-serif-display italic">{d.description}</p>
                  {d.price && <div className="mt-3 text-[color:var(--maroon)] font-semibold">₹{d.price}</div>}
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* Explore tiles */}
      <section className="section bg-[color:var(--cream)]" data-testid="home-explore">
        <div className="container-narrow">
          <div className="text-center mb-14">
            <div className="eyebrow mb-3">Explore</div>
            <h2 className="font-serif-display text-4xl md:text-5xl text-[color:var(--wood)]">Every way to visit</h2>
          </div>
          <div className="grid md:grid-cols-3 gap-4">
            {tiles.map((t, i) => (
              <Link key={t.to} to={t.to} className={`group relative overflow-hidden hover-zoom ${i === 0 ? "md:col-span-2 aspect-[16/10]" : "aspect-[4/5]"}`} data-testid={`explore-tile-${t.to.replace("/", "")}`}>
                <img src={t.img} alt="" className="w-full h-full object-cover" />
                <div className="absolute inset-0 bg-gradient-to-t from-[color:var(--wood)]/90 via-[color:var(--wood)]/20 to-transparent" />
                <div className="absolute bottom-6 left-6 right-6 text-[color:var(--cream)]">
                  <div className="font-serif-display text-3xl">{t.label}</div>
                  <div className="eyebrow mt-2 text-[color:var(--gold)] opacity-0 group-hover:opacity-100 transition duration-500">Discover →</div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
