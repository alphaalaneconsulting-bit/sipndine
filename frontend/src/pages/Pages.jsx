import { useEffect, useState } from "react";
import { api, mediaUrl } from "../lib/api";
import { PageHero, Diamond } from "../components/Layout";
import { Link } from "react-router-dom";

function usePage(slug, fallback = null) {
  const [c, setC] = useState(fallback);
  const [error, setError] = useState(false);

  useEffect(() => {
    let mounted = true;

    setError(false);

    api
      .get(`/content/${slug}`)
      .then((r) => {
        if (!mounted) return;

        const data = r.data;

        // If the backend returns an empty/incomplete page,
        // use the fallback content when available.
        if (
          fallback &&
          (!data ||
            (!data.title &&
              !data.eyebrow &&
              !data.hero_image &&
              !data.intro &&
              !data.body_html))
        ) {
          setC(fallback);
        } else {
          setC(data);
        }
      })
      .catch(() => {
        if (!mounted) return;

        setError(true);

        if (fallback) {
          setC(fallback);
        }
      });

    return () => {
      mounted = false;
    };
  }, [slug]);

  return { c, error };
}


/* =========================================================
   OUR STORY
   ========================================================= */

const OUR_STORY_FALLBACK = {
  slug: "our-story",
  title: "Our Story",
  eyebrow: "Since 2005 · Sector 7C",
  hero_image: "/restaurant/image5.jpeg",
  intro: "A family table that grew into a neighbourhood institution.",
  body_html: `
    <p>
      Sip 'n' Dine began the way most good restaurants do — around a family table,
      with recipes older than the room, and a stubborn belief that a meal in
      Chandigarh could feel like a meal in a home in old Lucknow.
      Two decades later, the plaque on our wall still reads
      <em>"Owners also eat here"</em>, and it is not a marketing line.
    </p>

    <p>
      Our kitchen is Awadhi at heart and Punjabi by neighbourhood —
      dum biryanis rested overnight, dal simmered for a full day,
      kebabs shaped by hand, breads pulled from a live tandoor.
      Our dining room is warm wood, soft brass light, floral corners
      for the private conversations, and a communal table for the ones
      you want to remember.
    </p>

    <p>
      Whether you're stopping in for a Sunday lunch, hosting an intimate
      anniversary, planning a wedding rehearsal, or feeding a marching band —
      we're a small, family-run house, and we still like to plate the first
      course ourselves.
    </p>
  `,
};

export function OurStory() {
  const { c, error } = usePage("our-story", OUR_STORY_FALLBACK);

  if (!c) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center bg-[color:var(--cream)]">
        <div className="text-center">
          <div className="eyebrow mb-3">Our Story</div>
          <p className="font-serif-display text-xl text-[color:var(--wood)]/70">
            Loading our story...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div data-testid="our-story-page">

      <PageHero
        eyebrow={c.eyebrow}
        title={c.title}
        image={c.hero_image}
        intro={c.intro}
      />

      <section className="section bg-[color:var(--cream)]">
        <div className="container-editorial">

          <Diamond />

          <div
            className="prose-warm"
            dangerouslySetInnerHTML={{
              __html: c.body_html || OUR_STORY_FALLBACK.body_html,
            }}
          />

          <div className="mt-12 text-center">
            <Link
              to="/book-table"
              className="btn-primary"
              data-testid="story-book-btn"
            >
              Reserve Your Table
            </Link>
          </div>

          {error && (
            <div className="mt-6 text-center text-xs uppercase tracking-widest text-[color:var(--wood)]/40">
              Showing our story from the site's saved content.
            </div>
          )}

        </div>
      </section>

    </div>
  );
}


/* =========================================================
   MENU
   ========================================================= */

export function Menu() {
  const { c } = usePage("menu");

  const [items, setItems] = useState([]);
  const [cat, setCat] = useState("All");
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    api
      .get("/menu")
      .then((r) => setItems(r.data))
      .catch(() => setItems([]));
  }, []);

  const cats = [
    "All",
    ...Array.from(new Set(items.map((i) => i.category))),
  ];

  const shown = items.filter(
    (i) =>
      (cat === "All" || i.category === cat) &&
      (filter === "all" ||
        (filter === "veg" ? i.veg : !i.veg))
  );

  if (!c) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center bg-[color:var(--cream)]">
        <p className="font-serif-display italic text-xl">
          Loading menu...
        </p>
      </div>
    );
  }

  return (
    <div data-testid="menu-page">

      <PageHero
        eyebrow={c.eyebrow}
        title={c.title}
        image={c.hero_image}
        intro={c.intro}
      />

      <section className="section bg-[color:var(--cream)]">

        <div className="container-narrow">

          <div className="flex flex-wrap gap-3 items-center justify-between border-b border-[color:var(--gold)]/25 pb-6 mb-10">

            <div className="flex flex-wrap gap-2">

              {cats.map((cn) => (
                <button
                  key={cn}
                  onClick={() => setCat(cn)}
                  className={`px-4 py-2 text-xs uppercase tracking-widest border ${
                    cat === cn
                      ? "bg-[color:var(--maroon)] text-[color:var(--cream)] border-[color:var(--maroon)]"
                      : "border-[color:var(--gold)]/40 text-[color:var(--wood)]/80 hover:border-[color:var(--gold)]"
                  }`}
                  data-testid={`menu-category-${cn.toLowerCase()}-tab`}
                >
                  {cn}
                </button>
              ))}

            </div>

            <div className="flex gap-2">

              {["all", "veg", "nonveg"].map((f) => (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  className={`px-3 py-2 text-xs uppercase tracking-widest border ${
                    filter === f
                      ? "bg-[color:var(--wood)] text-[color:var(--cream)] border-[color:var(--wood)]"
                      : "border-[color:var(--gold)]/40 text-[color:var(--wood)]/70"
                  }`}
                  data-testid={`menu-filter-${f}`}
                >
                  {f === "nonveg" ? "Non-Veg" : f}
                </button>
              ))}

            </div>

          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">

            {shown.map((d) => (
              <div
                key={d.id}
                className="card-warm hover-zoom overflow-hidden"
                data-testid={`menu-item-${d.id}`}
              >

                <div className="aspect-[4/3] overflow-hidden bg-[color:var(--wood)]/10">

                  {d.image_url ? (
                    <img
                      src={mediaUrl(d.image_url)}
                      alt={d.name}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center eyebrow text-[color:var(--wood)]/40">
                      Photo Coming Soon
                    </div>
                  )}

                </div>

                <div className="p-5">

                  <div className="flex items-center gap-2 justify-between">

                    <div className="flex items-center gap-2">
                      <span
                        className={
                          d.veg ? "tag-veg" : "tag-nonveg"
                        }
                      />

                      <span className="eyebrow text-[color:var(--gold)]">
                        {d.category}
                      </span>
                    </div>

                    {d.signature && (
                      <span className="eyebrow text-[color:var(--maroon)]">
                        Signature
                      </span>
                    )}

                  </div>

                  <h3 className="font-serif-display text-2xl mt-2 text-[color:var(--wood)]">
                    {d.name}
                  </h3>

                  <p className="text-sm text-[color:var(--wood)]/60 mt-2 font-serif-display italic">
                    {d.description}
                  </p>

                  {d.price != null && (
                    <div className="mt-3 text-[color:var(--maroon)] font-semibold">
                      ₹{d.price}
                    </div>
                  )}

                </div>

              </div>
            ))}

          </div>

          {shown.length === 0 && (
            <div className="text-center text-[color:var(--wood)]/50 py-20 font-serif-display italic text-xl">
              This section is being plated. Please check back soon.
            </div>
          )}

        </div>

      </section>

    </div>
  );
}


/* =========================================================
   BUFFET
   ========================================================= */

export function Buffet() {
  const { c } = usePage("buffet");

  if (!c) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center bg-[color:var(--cream)]">
        <p className="font-serif-display italic text-xl">
          Loading...
        </p>
      </div>
    );
  }

  return (
    <div data-testid="buffet-page">

      <PageHero
        eyebrow={c.eyebrow}
        title={c.title}
        image={c.hero_image}
        intro={c.intro}
      />

      <section className="section bg-[color:var(--cream)]">

        <div
          className="container-editorial prose-warm"
          dangerouslySetInnerHTML={{
            __html: c.body_html || "",
          }}
        />

        <div className="container-editorial text-center mt-8">

          <Link
            to="/book-table"
            className="btn-primary"
            data-testid="buffet-book-btn"
          >
            Reserve for Buffet
          </Link>

        </div>

      </section>

    </div>
  );
}


/* =========================================================
   GALLERY
   ========================================================= */

export function Gallery() {
  const { c } = usePage("gallery");

  const [imgs, setImgs] = useState([]);
  const [lightbox, setLightbox] = useState(null);

  useEffect(() => {
    api
      .get("/gallery")
      .then((r) => setImgs(r.data))
      .catch(() => setImgs([]));
  }, []);

  if (!c) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center bg-[color:var(--cream)]">
        <p className="font-serif-display italic text-xl">
          Loading gallery...
        </p>
      </div>
    );
  }

  return (
    <div data-testid="gallery-page">

      <PageHero
        eyebrow={c.eyebrow}
        title={c.title}
        image={c.hero_image}
        intro={c.intro}
      />

      <section className="section bg-[color:var(--cream)]">

        <div className="max-w-[1400px] mx-auto columns-1 sm:columns-2 lg:columns-3 gap-6 space-y-6">

          {imgs.map((im, i) => (
            <button
              key={im.id}
              onClick={() => setLightbox(im.url)}
              className="w-full break-inside-avoid hover-zoom"
              data-testid={`gallery-thumb-${i}`}
            >
              <img
                src={mediaUrl(im.url)}
                alt={im.caption || ""}
                className="w-full object-cover"
              />
            </button>
          ))}

        </div>

      </section>

      {lightbox && (
        <div
          className="fixed inset-0 z-[80] bg-[color:var(--wood)]/95 flex items-center justify-center p-6"
          onClick={() => setLightbox(null)}
          data-testid="gallery-lightbox"
        >
          <img
            src={mediaUrl(lightbox)}
            alt=""
            className="max-h-[90vh] max-w-[90vw] object-contain"
          />
        </div>
      )}

    </div>
  );
}


/* =========================================================
   ENQUIRY FORM
   ========================================================= */

function EnquiryForm({ kind, testid }) {

  const [f, setF] = useState({
    name: "",
    phone: "",
    email: "",
    date: "",
    guests: "",
    message: "",
  });

  const [sent, setSent] = useState(false);

  const submit = async (e) => {

    e.preventDefault();

    try {
      await api.post("/enquiries", {
        ...f,
        kind,
        guests: f.guests ? parseInt(f.guests) : null,
      });

      setSent(true);

      setF({
        name: "",
        phone: "",
        email: "",
        date: "",
        guests: "",
        message: "",
      });

    } catch (err) {
      console.error("Enquiry submission failed:", err);
    }
  };

  if (sent) {
    return (
      <div
        className="p-10 text-center border border-[color:var(--gold)]/40 bg-[color:var(--cream-muted)]"
        data-testid={`${testid}-sent`}
      >
        <div className="font-script text-[color:var(--gold)] text-4xl">
          Thank you.
        </div>

        <p className="font-serif-display italic text-lg mt-2">
          We'll be in touch within one working day.
        </p>
      </div>
    );
  }

  return (
    <form
      onSubmit={submit}
      className="grid sm:grid-cols-2 gap-4 p-8 border border-[color:var(--gold)]/30 bg-[color:var(--cream-muted)]"
      data-testid={testid}
    >

      <input
        required
        placeholder="Your name"
        value={f.name}
        onChange={(e) => setF({ ...f, name: e.target.value })}
        className="p-3 border border-[color:var(--gold)]/40 bg-transparent"
        data-testid={`${testid}-name`}
      />

      <input
        required
        placeholder="Phone"
        value={f.phone}
        onChange={(e) => setF({ ...f, phone: e.target.value })}
        className="p-3 border border-[color:var(--gold)]/40 bg-transparent"
        data-testid={`${testid}-phone`}
      />

      <input
        type="email"
        placeholder="Email (optional)"
        value={f.email}
        onChange={(e) => setF({ ...f, email: e.target.value })}
        className="p-3 border border-[color:var(--gold)]/40 bg-transparent"
        data-testid={`${testid}-email`}
      />

      <input
        type="date"
        placeholder="Event date"
        value={f.date}
        onChange={(e) => setF({ ...f, date: e.target.value })}
        className="p-3 border border-[color:var(--gold)]/40 bg-transparent"
        data-testid={`${testid}-date`}
      />

      <input
        type="number"
        min="1"
        placeholder="Guests"
        value={f.guests}
        onChange={(e) => setF({ ...f, guests: e.target.value })}
        className="p-3 border border-[color:var(--gold)]/40 bg-transparent"
        data-testid={`${testid}-guests`}
      />

      <div />

      <textarea
        placeholder="Tell us about your event…"
        rows="4"
        value={f.message}
        onChange={(e) => setF({ ...f, message: e.target.value })}
        className="p-3 border border-[color:var(--gold)]/40 bg-transparent sm:col-span-2"
        data-testid={`${testid}-message`}
      />

      <button
        type="submit"
        className="btn-primary sm:col-span-2 justify-center"
        data-testid={`${testid}-submit`}
      >
        Send Enquiry
      </button>

    </form>
  );
}


/* =========================================================
   BANQUETING
   ========================================================= */

export function Banqueting() {

  const { c } = usePage("banqueting");

  if (!c) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center bg-[color:var(--cream)]">
        <p className="font-serif-display italic text-xl">
          Loading...
        </p>
      </div>
    );
  }

  return (
    <div data-testid="banqueting-page">

      <PageHero
        eyebrow={c.eyebrow}
        title={c.title}
        image={c.hero_image}
        intro={c.intro}
      />

      <section className="section bg-[color:var(--cream)]">

        <div className="container-narrow grid md:grid-cols-2 gap-14 items-start">

          <div
            className="prose-warm"
            dangerouslySetInnerHTML={{
              __html: c.body_html || "",
            }}
          />

          <div>

            <div className="eyebrow mb-4">
              Enquire
            </div>

            <EnquiryForm
              kind="banqueting"
              testid="banqueting-form"
            />

          </div>

        </div>

      </section>

    </div>
  );
}


/* =========================================================
   CATERING
   ========================================================= */

export function Catering() {

  const { c } = usePage("catering");

  if (!c) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center bg-[color:var(--cream)]">
        <p className="font-serif-display italic text-xl">
          Loading...
        </p>
      </div>
    );
  }

  return (
    <div data-testid="catering-page">

      <PageHero
        eyebrow={c.eyebrow}
        title={c.title}
        image={c.hero_image}
        intro={c.intro}
      />

      <section className="section bg-[color:var(--cream)]">

        <div className="container-narrow grid md:grid-cols-2 gap-14 items-start">

          <div
            className="prose-warm"
            dangerouslySetInnerHTML={{
              __html: c.body_html || "",
            }}
          />

          <div>

            <div className="eyebrow mb-4">
              Plan With Us
            </div>

            <EnquiryForm
              kind="catering"
              testid="catering-form"
            />

          </div>

        </div>

      </section>

    </div>
  );
}


/* =========================================================
   OFFERS
   ========================================================= */

export function Offers() {

  const { c } = usePage("offers");

  const [offers, setOffers] = useState([]);

  useEffect(() => {
    api
      .get("/offers")
      .then((r) =>
        setOffers(r.data.filter((o) => o.active))
      )
      .catch(() => setOffers([]));
  }, []);

  if (!c) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center bg-[color:var(--cream)]">
        <p className="font-serif-display italic text-xl">
          Loading offers...
        </p>
      </div>
    );
  }

  return (
    <div data-testid="offers-page">

      <PageHero
        eyebrow={c.eyebrow}
        title={c.title}
        image={c.hero_image}
        intro={c.intro}
      />

      <section className="section bg-[color:var(--cream)]">

        <div className="container-narrow grid md:grid-cols-2 lg:grid-cols-3 gap-6">

          {offers.map((o) => (
            <div
              key={o.id}
              className="card-warm overflow-hidden"
              data-testid={`offer-card-${o.id}`}
            >

              {o.image_url && (
                <img
                  src={mediaUrl(o.image_url)}
                  alt=""
                  className="w-full h-56 object-cover"
                />
              )}

              <div className="p-6">

                <div className="eyebrow text-[color:var(--gold)]">
                  {o.subtitle}
                </div>

                <h3 className="font-serif-display text-2xl mt-2 text-[color:var(--wood)]">
                  {o.title}
                </h3>

                <p className="mt-3 text-sm text-[color:var(--wood)]/70 font-serif-display italic leading-relaxed">
                  {o.description}
                </p>

                {o.valid_till && (
                  <div className="mt-4 text-xs uppercase tracking-widest text-[color:var(--maroon)]">
                    Valid: {o.valid_till}
                  </div>
                )}

              </div>

            </div>
          ))}

        </div>

      </section>

    </div>
  );
}


/* =========================================================
   MEMBERSHIP
   ========================================================= */

export function Membership() {

  const { c } = usePage("membership");

  const [tiers, setTiers] = useState([]);
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);

  useEffect(() => {
    api
      .get("/membership")
      .then((r) => setTiers(r.data))
      .catch(() => setTiers([]));
  }, []);

  const submit = async (e) => {

    e.preventDefault();

    try {
      await api.post("/membership/waitlist", {
        email,
      });

      setSent(true);
      setEmail("");

    } catch (err) {
      console.error("Waitlist submission failed:", err);
    }
  };

  if (!c) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center bg-[color:var(--cream)]">
        <p className="font-serif-display italic text-xl">
          Loading membership...
        </p>
      </div>
    );
  }

  return (
    <div data-testid="membership-page">

      <PageHero
        eyebrow={c.eyebrow}
        title={c.title}
        image={c.hero_image}
        intro={c.intro}
      />

      <section className="section bg-[color:var(--cream)]">

        <div className="container-narrow">

          <div className="grid md:grid-cols-3 gap-6">

            {tiers.map((t) => (
              <div
                key={t.id}
                className={`p-8 border ${
                  t.highlighted
                    ? "border-[color:var(--gold)] bg-[color:var(--wood)] text-[color:var(--cream)]"
                    : "border-[color:var(--gold)]/30 card-warm"
                }`}
                data-testid={`tier-card-${t.id}`}
              >

                <div className="eyebrow text-[color:var(--gold)]">
                  {t.tagline}
                </div>

                <h3 className="font-serif-display text-3xl mt-2">
                  {t.name}
                </h3>

                <div className="mt-2 text-sm opacity-70">
                  {t.price}
                </div>

                <ul className="mt-6 space-y-3">

                  {t.benefits.map((b, i) => (
                    <li
                      key={i}
                      className="text-sm flex gap-2 items-start"
                    >
                      <i className="fa-solid fa-diamond text-[8px] text-[color:var(--gold)] mt-2" />

                      <span className="font-serif-display italic">
                        {b}
                      </span>
                    </li>
                  ))}

                </ul>

              </div>
            ))}

          </div>

          <div className="mt-20 text-center max-w-xl mx-auto">

            <div className="eyebrow mb-3">
              Be the first to know
            </div>

            <h3 className="font-serif-display text-3xl">
              Join the Privilege waitlist
            </h3>

            {sent ? (
              <div
                className="mt-8 font-script text-3xl text-[color:var(--gold)]"
                data-testid="waitlist-sent"
              >
                You're on the list.
              </div>
            ) : (
              <form
                onSubmit={submit}
                className="mt-8 flex gap-3"
                data-testid="waitlist-form"
              >

                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="your@email.com"
                  className="flex-1 p-3 border border-[color:var(--gold)]/40 bg-transparent"
                  data-testid="waitlist-email-input"
                />

                <button
                  className="btn-primary"
                  type="submit"
                  data-testid="waitlist-submit-btn"
                >
                  Notify Me
                </button>

              </form>
            )}

          </div>

        </div>

      </section>

    </div>
  );
}


/* =========================================================
   BOOK TABLE
   ========================================================= */

export function BookTable() {

  const { c } = usePage("book-table");

  const [f, setF] = useState({
    name: "",
    phone: "",
    email: "",
    date: "",
    time: "19:30",
    party_size: 2,
    occasion: "",
    notes: "",
  });

  const [sent, setSent] = useState(null);

  const submit = async (e) => {

    e.preventDefault();

    try {

      const r = await api.post("/bookings", {
        ...f,
        party_size: parseInt(f.party_size),
      });

      setSent(r.data.id);

    } catch (err) {
      console.error("Booking failed:", err);
    }
  };

  if (!c) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center bg-[color:var(--cream)]">
        <p className="font-serif-display italic text-xl">
          Loading...
        </p>
      </div>
    );
  }

  return (
    <div data-testid="book-table-page">

      <PageHero
        eyebrow={c.eyebrow}
        title={c.title}
        image={c.hero_image}
        intro={c.intro}
      />

      <section className="section bg-[color:var(--cream)]">

        <div className="container-editorial">

          {sent ? (

            <div
              className="text-center p-12 border border-[color:var(--gold)]/40 bg-[color:var(--cream-muted)]"
              data-testid="booking-sent"
            >

              <div className="font-script text-6xl text-[color:var(--gold)]">
                Thank you.
              </div>

              <p className="mt-6 font-serif-display italic text-xl">
                Your table is being arranged. Our team will confirm shortly.
              </p>

              <div className="mt-4 text-xs uppercase tracking-widest text-[color:var(--wood)]/60">
                Confirmation Ref · {sent.slice(0, 8)}
              </div>

              <Link
                to="/"
                className="btn-outline-gold mt-8 inline-block"
                data-testid="booking-home-btn"
              >
                Back to Home
              </Link>

            </div>

          ) : (

            <form
              onSubmit={submit}
              className="grid sm:grid-cols-2 gap-4 p-8 border border-[color:var(--gold)]/30 bg-[color:var(--cream-muted)]"
              data-testid="booking-form"
            >

              <input
                required
                placeholder="Full name"
                value={f.name}
                onChange={(e) => setF({ ...f, name: e.target.value })}
                className="p-3 border border-[color:var(--gold)]/40 bg-transparent"
                data-testid="booking-name"
              />

              <input
                required
                placeholder="Phone"
                value={f.phone}
                onChange={(e) => setF({ ...f, phone: e.target.value })}
                className="p-3 border border-[color:var(--gold)]/40 bg-transparent"
                data-testid="booking-phone"
              />

              <input
                type="email"
                placeholder="Email"
                value={f.email}
                onChange={(e) => setF({ ...f, email: e.target.value })}
                className="p-3 border border-[color:var(--gold)]/40 bg-transparent sm:col-span-2"
                data-testid="booking-email"
              />

              <input
                required
                type="date"
                value={f.date}
                onChange={(e) => setF({ ...f, date: e.target.value })}
                className="p-3 border border-[color:var(--gold)]/40 bg-transparent"
                data-testid="booking-date"
              />

              <input
                required
                type="time"
                value={f.time}
                onChange={(e) => setF({ ...f, time: e.target.value })}
                className="p-3 border border-[color:var(--gold)]/40 bg-transparent"
                data-testid="booking-time"
              />

              <input
                required
                type="number"
                min="1"
                max="30"
                placeholder="Party size"
                value={f.party_size}
                onChange={(e) => setF({ ...f, party_size: e.target.value })}
                className="p-3 border border-[color:var(--gold)]/40 bg-transparent"
                data-testid="booking-party"
              />

              <input
                placeholder="Occasion (optional)"
                value={f.occasion}
                onChange={(e) => setF({ ...f, occasion: e.target.value })}
                className="p-3 border border-[color:var(--gold)]/40 bg-transparent"
                data-testid="booking-occasion"
              />

              <textarea
                rows="3"
                placeholder="Special requests"
                value={f.notes}
                onChange={(e) => setF({ ...f, notes: e.target.value })}
                className="p-3 border border-[color:var(--gold)]/40 bg-transparent sm:col-span-2"
                data-testid="booking-notes"
              />

              <button
                type="submit"
                className="btn-primary sm:col-span-2 justify-center"
                data-testid="booking-submit-btn"
              >
                Reserve My Table
              </button>

              <div className="sm:col-span-2 text-center text-xs text-[color:var(--wood)]/50 uppercase tracking-widest">
                or call +91 172 4641656
              </div>

            </form>

          )}

        </div>

      </section>

    </div>
  );
}


/* =========================================================
   CONTACT
   ========================================================= */

export function Contact() {

  const { c } = usePage("contact");

  const [s, setS] = useState(null);

  useEffect(() => {
    api
      .get("/settings")
      .then((r) => setS(r.data))
      .catch(() => setS(null));
  }, []);

  if (!c || !s) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center bg-[color:var(--cream)]">
        <p className="font-serif-display italic text-xl">
          Loading contact information...
        </p>
      </div>
    );
  }

  return (
    <div data-testid="contact-page">

      <PageHero
        eyebrow={c.eyebrow}
        title={c.title}
        image={c.hero_image}
        intro={c.intro}
      />

      <section className="section bg-[color:var(--cream)]">

        <div className="container-narrow grid md:grid-cols-2 gap-14">

          <div>

            <div className="eyebrow mb-3">
              The Address
            </div>

            <p className="font-serif-display text-xl leading-relaxed">
              {s.address}
            </p>

            <div className="hairline my-8" />

            <div className="eyebrow mb-3">
              Reach Us
            </div>

            {s.phones.map((p, i) => (
              <a
                key={i}
                href={`tel:${p}`}
                className="block text-lg font-serif-display text-[color:var(--maroon)] hover:opacity-70"
                data-testid={`contact-phone-${i}`}
              >
                {p}
              </a>
            ))}

            <a
              href={`mailto:${s.email}`}
              className="block mt-3 text-lg font-serif-display text-[color:var(--maroon)]"
              data-testid="contact-email"
            >
              {s.email}
            </a>

            <div className="hairline my-8" />

            <div className="eyebrow mb-3">
              Hours
            </div>

            {s.hours.map((h, i) => (
              <div
                key={i}
                className="text-sm mb-1"
              >
                <span className="text-[color:var(--gold)] font-semibold">
                  {h.day}
                </span>
                {" · "}
                {h.hours}
              </div>
            ))}

          </div>

          <div>

            <iframe
              title="Sip 'n' Dine map"
              src={s.map_embed_url}
              className="w-full h-full min-h-[420px] border-0"
              data-testid="contact-map"
            />

          </div>

        </div>

      </section>

    </div>
  );
}
