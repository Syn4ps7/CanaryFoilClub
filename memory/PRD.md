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
- 6 sections : Hero, Différence (3 piliers), Expériences (3 tarifs), Corporate Sunset 890€, Revendeur Fliteboard, Footer réassurance
- Formulaire de réservation démo connecté au backend (persisté en MongoDB, toast succès/erreur)
- Motion premium : lenis smooth scroll, scroll-reveals staggered, micro-interactions hover, marquee éditorial
- data-testid sur tous les éléments interactifs

## Verified
- POST /api/booking + GET /api/bookings (curl, 2 bookings en base dont 1 via l'UI)
- Parcours complet screenshot : switch EN, ouverture modal, soumission formulaire Corporate, toast succès
- Rendu visuel hero, expériences, corporate, reseller, footer

## Backlog
- P0 : Remplacer les coordonnées fictives (WhatsApp, Instagram) par les vraies
- P1 : Paiement Stripe réel sur les expériences (clé test dispo dans le pod)
- P1 : Notification email/WhatsApp au propriétaire à chaque demande de réservation (Resend/Twilio)
- P1 : Page admin ou listing privé des demandes de réservation
- P2 : Vidéo hero en arrière-plan (boucle eFoil) à la place de l'image
- P2 : Galerie Instagram / avis clients
- P2 : SEO multilingue (hreflang, métadonnées par langue), mentions légales réelles
