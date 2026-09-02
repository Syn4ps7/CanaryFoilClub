# PRD — Canary Foil Club

## Original Problem Statement
Site vitrine One-Page ultra-premium pour le Canary Foil Club : service exclusif d'initiation/excursion en surf électrique (eFoil Fliteboard) à Costa Adeje, Ténérife. Positionnement luxe : aucune location libre, encadrement 100% par casques radio BB Talkin, camp de base mobile (van haut de gamme). Cible : touristes 5 étoiles, couples, entreprises (team-building). Objectif : conversion vers réservation en ligne. Sections requises : Hero, 3 piliers (Tech/Éco, Coaching VIP radio, Agilité mobile), grille tarifaire (Discovery 145€, Duo VIP 280€, Option Drone 4K +50€), offre B2B Corporate Sunset (890€), section Revendeur Officiel Fliteboard (Test Drive), footer réassurance (Stripe, WhatsApp VIP, Instagram, mentions légales).

## User Personas
- Touriste fort pouvoir d'achat en hôtel 5★ (Bahía del Duque, Abama…) cherchant une expérience exclusive et sécurisée
- Couple en voyage de luxe (Duo VIP Experience)
- Office manager / DRH organisant un team-building premium (Corporate Sunset)
- Passionné de glisse haut de gamme envisageant l'achat d'un Fliteboard (Test Drive)

## User Choices (confirmed)
- Langues : FR / EN / ES (sélecteur dans la navbar, FR par défaut)
- Réservation : formulaire démo (pas de paiement réel) — stocké en base, toast de confirmation
- Style : délégué au designer — direction "Luxury Oceanic" (océan profond #050B14, cyan #00F0FF, or #D4AF37)
- Contacts : fictifs (à remplacer) — WhatsApp +34 600 000 000, Instagram @canaryfoilclub
- Visuels : banque d'images libre de droits (Unsplash)

## Architecture
- Frontend : React 19 + Tailwind + framer-motion (révélations scroll, hero kinétique masqué ligne par ligne, intro d'ouverture) + lenis (smooth scroll) + sonner (toasts). i18n maison via LanguageContext + translations.js (FR/EN/ES).
- Backend : FastAPI — POST /api/booking (création demande), GET /api/bookings (liste), GET /api/ (health). MongoDB via motor, ids UUID string, created_at UTC ISO.
- Composants : Navbar (switcher langue, drawer mobile), Hero (parallax + reveal masqué), Marquee (ruban éditorial lent), Pillars (chapitres numérotés 01/02/03), Experiences (grille 3 cartes, Duo mise en avant or), Corporate (B2B, image parallax), Reseller (Test Drive), BookingModal (slide-over), Footer (badges paiement, grand wordmark outline).

## Implemented (2026-09-02)
- One-page complet FR/EN/ES avec bascule instantanée
- Intro cinématique + hero kinétique avec parallax
- Vidéo hero en boucle (eFoil golden hour, Pexels 28493916, compressée 1080p MP4 H.264 9.8MB + WebM/VP9 1600px 10.7MB, poster Unsplash en fallback) — `/frontend/public/hero-efoil.{mp4,webm}`
- 6 sections : Hero, Différence (3 piliers), Expériences (3 tarifs), Corporate Sunset 890€, Revendeur Fliteboard, Footer réassurance
- Formulaire de réservation démo connecté au backend (persisté en MongoDB, toast succès/erreur)
- Alerte email à chaque réservation via Resend managé Emergent (`/app/backend/emailer.py`, proxy integrations.emergentagent.com, gate guardrails G2/G3, template HTML dark luxe, Reply-To = email client). Destinataire : OWNER_EMAIL dans backend/.env — actuellement placeholder `bookings@canaryfoilclub.com` (REFUSÉ par le proxy car domaine inexistant : l'alerte échoue en silence, la réservation reste enregistrée). Remplacer par le vrai email du propriétaire pour activer.
- Motion premium : lenis smooth scroll, scroll-reveals staggered, micro-interactions hover, marquee éditorial
- data-testid sur tous les éléments interactifs

## Verified
- POST /api/booking + GET /api/bookings (curl, bookings en base)
- Alerte email : envoi test au proxy Resend → 202 + id (delivered@resend.dev) ; avec placeholder fictif → 422 "undeliverable recipient" (comportement attendu, non bloquant)
- Vidéo hero : lecture confirmée en headless (currentTime 7.1s → 9.7s, readyState 4) ; curl 206 video/mp4
- Parcours complet screenshot : switch EN, modal, soumission Corporate, toast succès

## Backlog
- P0 : Fournir le VRAI email du propriétaire pour activer les alertes (OWNER_EMAIL dans backend/.env) + vraies coordonnées WhatsApp/Instagram
- P1 : Paiement Stripe réel sur les expériences (clé test dispo dans le pod)
- P1 : Notification WhatsApp (Twilio) en plus de l'email
- P1 : Page admin ou listing privé des demandes de réservation
- P2 : Galerie Instagram / avis clients
- P2 : SEO multilingue (hreflang, métadonnées par langue), mentions légales réelles
- P2 : Confirmation email automatique au client après sa demande
