# Sip 'n' Dine — Product Requirements

## Problem statement
Premium editorial website for **Sip 'n' Dine** — Indian fine dining in Sector 7C, Chandigarh — with a self-service admin dashboard so the owner (alphaalaneconsulting@gmail.com) can edit every tab without a developer.

## Users
- **Guests** — book a table, view menu (AI-generated dish photos), explore buffet / banqueting / catering / offers / membership, contact.
- **Owner (admin)** — logs in at `/admin`, edits every page, manages reservations & enquiries, regenerates AI dish photos, updates global settings.

## Architecture
- **Backend** — FastAPI + MongoDB (motor). JWT auth (bcrypt). Emergent LLM key + `emergentintegrations` for Gemini `gemini-3.1-flash-image-preview` (Nano Banana) image generation. Static `/api/uploads/*` for generated images.
- **Frontend** — React 19 + Tailwind + Shadcn/UI + framer-motion. React Router. Sonner toasts. Cormorant Garamond + Alex Brush + Plus Jakarta Sans fonts.

## Implemented (Feb 2026)
- 11 public landing pages: Home, Our Story, Menu, Buffet, Gallery (masonry + lightbox), Banqueting, Catering, Offers, Membership, Book a Table, Location & Contact.
- Editorial cinematic hero, "Why Chandigarh Loves Us" recognition section, signature dishes teaser, explore-tiles bento, editorial footer with hours/map.
- Menu: 20 seeded signature dishes across Starters/Tandoor/Mains/Biryani/Breads/Desserts/Drinks with veg/non-veg filter + category tabs.
- AI food photo generation via Gemini Nano Banana (per-dish "AI Photo" button + background refresh at first startup).
- Booking, banqueting, catering enquiry & waitlist forms — all persist to Mongo.
- Admin: JWT login, dashboard with 10 tabs — Reservations manager, per-page Content Editor (rich body_html), Menu manager (CRUD + AI regen), Global Settings (address, phones, email, hours, socials, map embed, logo URL), Recognition CRUD, Offers CRUD, Membership Tiers CRUD, Gallery CRUD, Enquiries list, Waitlist list.
- Seeded content, recognition, offers, membership tiers, gallery, admin account on startup.

## Client questions from latest doc (already handled)
- Logo font change → logo is code-drawn and the logo URL field in Global Settings lets the owner upload a new mark.
- Updated restaurant phone number → editable in Global Settings > Phones.
- Signature dish photos & menu updates → AI photos live now; owner can edit every dish and regenerate images.
- Privilege membership pricing → tiers editable; "Coming Soon" price placeholder + waitlist active.
- Restaurant renovation exterior → interior hero in place; owner can swap hero image via Content Editor.
- "Warmer" tab naming → "Our Story", "Book a Table", "Location & Contact" etc. already warm.

## Credentials
- Admin: `alphaalaneconsulting@gmail.com` / `SipnDine@2026`

## Backlog / P1 next
- Object-storage image uploader inside admin (currently paste URL).
- Rich-text WYSIWYG editor for body_html (currently HTML textarea).
- Google/Zomato live rating pull.
- Resend email notifications when a new booking / enquiry arrives.
- Multi-admin roles.
