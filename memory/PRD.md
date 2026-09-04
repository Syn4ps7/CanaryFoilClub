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
- Email de confirmation automatique au client après sa demande (`notify_client`), rédigé dans la langue du site au moment de l'envoi (FR/EN/ES, champ `lang` du booking), récapitulatif expérience/date/participants, aucun lien externe (tel: uniquement)
- Motion premium : lenis smooth scroll, scroll-reveals staggered, micro-interactions hover, marquee éditorial
- data-testid sur tous les éléments interactifs

## Implemented (2026-06) — Admin Dashboard /admin
- Auth : compte admin unique défini dans backend/.env (ADMIN_EMAIL / ADMIN_PASSWORD), seedé en Mongo `users` avec hash bcrypt au démarrage, JWT HS256 12h (Bearer, localStorage `cfc_admin_token`), brute force 5 échecs → 429 pendant 15 min (clé = email). `/app/backend/auth.py`
- Routes protégées : GET /api/auth/me, GET /api/bookings, GET /api/admin/stats, PATCH /api/admin/bookings/{id} {status|partner|partner_name}
- KPIs (`/app/backend/stats.py`) : CA jour/mois/total (statuts confirmed+completed uniquement, basé sur la date de session), sessions, taux d'occupation jour/mois (3 planches × 4 créneaux = 12 slots/jour ; discovery=min(n,3) slots, duo=2, testdrive=1, corporate=9, drone=0), répartition CA B2C / Corporate 890 € / Options Drone, commissions partenaires 20 % sur réservations `partner=true`, 10 dernières réservations
- Grille tarifaire : Discovery 145 €×pers, Duo 280 € forfait, Drone 50 €×pers, Corporate 890 € forfait, Test Drive 0 €
- Frontend : react-router (`/` Landing, `/admin`), AdminLogin, AdminDashboard (KpiCard, RevenueSplit, BookingsTable avec select statut + toggle partenaire), design Luxury Oceanic, French-only
- Formulaire public : case « Réservation apportée par un partenaire » + nom du partenaire (FR/EN/ES)
- Testé : testing_agent iteration_1 (backend 10/10 après fix lockout, frontend 100 %)

## Implemented (2026-06) — Admin v2
- Identifiants provisoires : `admin` / `admin` (ADMIN_EMAIL / ADMIN_PASSWORD dans backend/.env, login accepte un identifiant non-email)
- Capacité dynamique : `settings` Mongo {boards 1-6 (défaut 3), slots_per_day 1-6 (défaut 6)} — éditable depuis le dashboard (CapacitySettings) ; occupation = sessions-planche / (planches × créneaux) ; corporate = toutes les planches × 3 créneaux
- Email de confirmation au client (FR/EN/ES, `notify_confirmed`) envoyé quand le statut passe à « confirmed » depuis le dashboard ; flag `confirmation_email_sent` stocké et exposé
- Page /admin/bookings : recherche (nom/email/tél/hôtel/partenaire), filtres statut + dates de session, résumé CA encaissable, export CSV (`;`, BOM, colonnes compta dont commission)
- Page /admin/planning : grille créneaux × planches par jour, navigation date, affectation créneau (`slot`, 0 = retirer), liste « à placer », surbooking signalé
- Layout admin avec navigation (Vue d'ensemble / Réservations / Planning), react-router `/admin/*`
- Testé : testing_agent iteration_2 (backend 25/25, frontend 100 %)

## Implemented (2026-06) — Admin v3
- Flèche « remonter en haut » sur la landing (`ScrollTop.jsx`, apparaît après 80 % de viewport, scroll Lenis)
- Changement de mot de passe depuis le dashboard (icône clé → modal, POST /api/auth/change-password, min 8 caractères) ; `seed_admin` ne réécrit plus le hash au démarrage (le .env sert uniquement à la création initiale)
- Météo du spot (Open-Meteo, sans clé, cache 30 min) sur la vue jour du planning : vent moyen/rafales/direction, houle/période/direction, température, barres horaires 8h-20h, recommandation de crique (Playa del Duque-Fañabé / La Caleta-Playa Paraíso / El Puertito / Puerto Colón) avec niveau idéal-bon-limite-déconseillé ; fenêtre -60 j / +15 j
- Vue semaine du planning (GET /api/admin/planning/week) : 7 cartes lundi→dimanche, occupation, sessions, CA, en attente, « jour creux », clic → vue jour
- Typo des chiffres : Outfit (tabular-nums) sur tous les KPIs/montants admin
- Testé : testing_agent iteration_3 (backend 37/37, frontend 100 %) ; fix erreur météo hors horizon (message court)

## Implemented (2026-06) — Admin v4
- Créneaux horaires : `settings.slot_times` (HH:MM, un par créneau, défaut 09:00/10:30/12:00/13:30/15:00/16:30, validés + complétés par +90 min) éditables dans « Capacité & horaires » ; affichés dans le planning (heure + Cn), les selects de créneau, et dans les emails client (confirmation + rappel)
- Rappel veille automatique (`reminders.py`) : boucle asyncio toutes les 15 min, à partir de 17h heure Canaries, envoie une fois par réservation confirmée de demain (`reminder_sent`) un email FR/EN/ES avec heure du créneau, point de RDV, accès, conditions vent/houle prévues ; POST /api/admin/reminders/run (manuel), POST /api/admin/bookings/{id}/reminder (envoi/renvoi individuel, bouton « Rappel J-1 » dans les tables)
- Point de RDV par jour : recommandation météo (4 spots avec adresse d'accès) ou choix manuel (`day_plans`, GET/PUT /api/admin/planning/meeting-point) depuis le panneau doré sous la météo
- Testé : testing_agent iteration_4 (backend 19/19 nouveaux, frontend 100 %)

## Implemented (2026-06) — Admin v5 : Avis clients + Bilan hebdo
- Avis clients (`engagement.py`) : job quotidien (≥ 9h Canaries) envoie aux sessions confirmées/réalisées de la veille un email FR/EN/ES avec lien `SITE_URL/avis/{review_token}` (bouton CTA https) ; page publique `/avis/:token` (note 1-5, commentaire, nom affiché, langue du client) ; POST unique par réservation (409) ; modération admin (onglet « Avis » : publier/masquer, mettre en avant, supprimer) ; section « Ils ont volé avec nous » sur la landing (GET /api/reviews, approuvés uniquement, favoris en premier, masquée si vide) ; colonne « Avis » dans les tables (Demander / Demandé / Reçu)
- Bilan hebdo : job lundi ≥ 8h Canaries (dédupliqué dans `weekly_reports`) → email propriétaire : CA, sessions, occupation, commissions, jour par jour avec « Jour creux », CA par offre, semaine à venir (libre / confirmées / en attente), demandes en attente, note moyenne ; carte « Bilan hebdo » sur le dashboard (aperçu + envoi manuel) ; POST /api/admin/reports/weekly/send?to= pour test
- `SITE_URL` ajouté dans backend/.env (à mettre à jour lors du déploiement sur le vrai domaine)
- Testé : testing_agent iteration_5 (backend 17/17 nouveaux, frontend 100 %)

## Implemented (2026-06) — Admin v6 : Bons cadeaux + Réponse aux avis
- Bons cadeaux (`vouchers.py`) : section « Offrir un vol » + modal (acheteur, destinataire, message, Discovery ×1-3 / Duo) → POST /api/vouchers (statut pending, code unique CFC-XXXX-XXXX, email propriétaire) ; activation admin (statut paid → paid_at, expires_at +365 j, email FR/EN/ES à l'acheteur avec le code) ; GET /api/vouchers/check/{code} public ; champ « Code cadeau » dans le formulaire de réservation avec validation live → remise appliquée (`booking.discount`, `price_of` = base − remise) et bon marqué redeemed ; onglet admin « Bons cadeaux » (activer / renvoyer / annuler / remettre en circulation) ; CA « Bons cadeaux » dans la répartition (encaissé à l'activation) ; colonnes CSV bon_cadeau / remise_eur
- Réponse aux avis : PATCH /api/admin/reviews/{id} {reply} (replied_at) ; ReplyBox dans l'onglet Avis ; bloc « Réponse de Canary Foil Club » sur les cartes de la landing
- Fix régression : champ `created_at` du modèle Booking restauré (POST /api/booking plantait) ; sérialisation des avis dont created_at est un datetime
- GitHub : l'utilisateur doit utiliser « Save to GitHub » (dépôt Syn4ps7/CanaryFoilClub)
- Testé : testing_agent iteration_6 (backend 23/23, frontend 100 %)

## Bug fix (2026-06) — Panneau de réservation non défilable
- Cause : Lenis interceptait la molette, le panneau latéral (overflow-y-auto) ne défilait pas jusqu'au bouton « Envoyer »
- Fix : `data-lenis-prevent` sur booking-modal et gift-modal ; `lenis.stop()/start()` + `overflow:hidden` sur html/body pendant l'ouverture d'un panneau (Landing.jsx)
- Testé : testing_agent iteration_7 + iteration_8 (100 %)

## Implemented (2026-06) — Bon cadeau PDF
- `voucher_pdf.py` (reportlab + qrcode) : A5 paysage, design Luxury Oceanic, code, valeur, destinataire, message, validité, QR vers `SITE_URL/?code=…` (ouvre le formulaire avec le code prérempli)
- Le proxy email ne supporte pas les pièces jointes → bouton doré « Télécharger le bon cadeau (PDF) » dans l'email d'activation, lien signé `GET /api/vouchers/{code}/pdf?k={download_token}` (403 tant que non activé) ; `GET /api/admin/vouchers/{id}/pdf` (Bearer) + bouton PDF dans l'onglet Bons cadeaux
- Testé : testing_agent iteration_9 (backend 9/9, frontend 100 %)

## Implemented (2026-06) — Galerie photos & vidéos
- Stockage Emergent Object Storage (`storage.py`, EMERGENT_LLM_KEY dans backend/.env, préfixe `canary-foil-club/gallery/`) ; métadonnées Mongo `gallery` (soft-delete)
- API : GET /api/gallery, GET /api/gallery/{id}/file (public, cache 24 h), POST /api/admin/gallery (multipart, 60 Mo, images + vidéos), PATCH légende, POST reorder, DELETE (soft)
- Admin onglet « Galerie » : upload multiple + drag & drop avec progression, légende, ordre (flèches), suppression
- Landing : section « Nos vols, en vrai » (#gallery, entre Corporate et Avis), grille cinématique, vidéos en autoplay muet, lightbox (prev/next/Esc) ; masquée si vide ; images de stock conservées
- Header admin : 6 onglets sur une ligne (whitespace-nowrap)
- Testé : testing_agent iteration_10 (backend 12/12, frontend 100 %)

## Vérification (2026-06) — Lien réservations ↔ CA
- Règle confirmée : CA = réservations `confirmed` + `completed` (montant net après bon cadeau, à la date de session) + bons cadeaux activés (paid_at). `pending`/`cancelled` hors CA. Passage confirmée → réalisée : CA inchangé, bascule dans revenue_by_status.
- Ajout `revenue_by_status` / `sessions_by_status` dans /api/admin/stats + panneau « Réservations → chiffre d'affaires » (StatusBreakdown) avec ligne d'auto-vérification (somme des statuts = CA total, sessions = confirmées + réalisées)
- À venir (Stripe) : paiement réussi → statut `confirmed` automatique (webhook), bon cadeau → `paid` automatique
- Testé : testing_agent iteration_11 (backend 13/13, frontend 100 %)

## Bug fix (2026-06) — CA du jour/mois ne bougeait pas à la confirmation
- Cause : CA jour/mois calculé à la date de session ; confirmer une réservation d'un autre jour/mois ne changeait rien
- Fix : `confirmed_at` posé au premier passage confirmed/completed ; revenue.today/month calculés à la date d'encaissement (`cash_date` = confirmed_at, fallback created_at) ; sessions/occupation restent à la date de session ; KPIs renommés « CA encaissé aujourd'hui / ce mois » + `confirmations {today, month}`
- Testé : testing_agent iteration_12 (100 %)

## Implemented (2026-06) — Courbe du CA + CGV
- GET /api/admin/stats/revenue-series?days=30|90 (7-365) : série journalière par date d'encaissement (bookings confirmées/réalisées via confirmed_at + bons cadeaux paid_at), cumul, total, meilleur jour ; `RevenueChart.jsx` (recharts ComposedChart : barres CA du jour + aire dorée cumul, bascule 30 j / 90 j, tooltip) en tête du dashboard
- CGV : `i18n/terms.js` (8 articles FR/EN/ES, texte fourni par l'utilisateur), `TermsModal.jsx` (data-lenis-prevent, Esc), lien « CGV » dans le footer (`footer.terms`)
- Testé : testing_agent iteration_13 (backend 6/6, frontend 100 %)

## Bug fix + Case CGV (2026-06)
- Bug : modal CGV décentrée/coupée (transform framer-motion écrasait les classes -translate-x/y). Fix : conteneur fixed inset-0 flex centré (wrapper pointer-events-none), z-110/111 pour passer au-dessus des panneaux latéraux ; même correctif sur la modal « Changer le mot de passe »
- Case « J'ai lu et j'accepte les CGV » obligatoire (`TermsCheckbox.jsx`, required + toast) dans BookingModal et GiftModal, lien inline ouvrant la modal CGV ; clés `footer.acceptTerms / termsShort / termsRequired` FR/EN/ES
- Testé : testing_agent iteration_14 (frontend 7/7, 3 viewports)
- Âge minimum passé de 16 à 14 ans dans les CGV (FR/EN/ES, article 3) — vérifié par screenshot

## Implemented (2026-06) — Accord parental
- Formulaire : case « participant(s) mineur(s) 14-17 ans » → panneau ambre (rappel autorisation parentale écrite) + case d'engagement obligatoire ; backend `minor` / `minor_consent` (400 si mineur sans engagement) ; email propriétaire ligne « Mineur(s) »
- Admin : badge « Mineur · autorisation à recevoir / reçue » cliquable dans les tables (PATCH `parental_auth_received`)
- Testé : testing_agent iteration_15 (backend 7/7, frontend 8/8)

## Verified
- POST /api/booking + GET /api/bookings (curl, bookings en base)
- Alerte email : envoi test au proxy Resend → 202 + id (delivered@resend.dev) ; avec placeholder fictif → 422 "undeliverable recipient" (comportement attendu, non bloquant)
- Vidéo hero : lecture confirmée en headless (currentTime 7.1s → 9.7s, readyState 4) ; curl 206 video/mp4
- Parcours complet screenshot : switch EN, modal, soumission Corporate, toast succès

## Backlog
- P0 : Fournir le VRAI email du propriétaire pour activer les alertes (OWNER_EMAIL dans backend/.env) + vraies coordonnées WhatsApp/Instagram
- P1 : Paiement Stripe réel sur les expériences (clé test dispo dans le pod)
- P1 : Notification WhatsApp (Twilio) en plus de l'email
- P1 : Admin — changement de mot de passe depuis le dashboard, export CSV, filtre/recherche sur toutes les réservations, alerte email au client lors de la confirmation
- P2 : Galerie Instagram / avis clients
- P2 : SEO multilingue (hreflang, métadonnées par langue), mentions légales réelles
