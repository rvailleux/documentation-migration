# Documentation Improvement Plan

> Created from full-site review of [Apizee Legacy Docs](https://apizeelegacy.gitbook.io/apizeelegacy-docs). 
> Legend: 🔴 Critical | 🟠 High | 🟡 Medium | 🟢 Low

---

## Quick Wins — Immediate Action Items

| Priority | Action | ETA |
|----------|--------|-----|
| 🔴 | Replace the homepage with a proper help center homepage (search hero, category cards, quick-access chips) | Immediate |
| 🔴 | Fix the "Diag Help Des****k" garbled text in the FAQ title | Immediate |
| 🔴 | Address the "apizeelegacy" domain — clarify version, add banner, or migrate | Immediate |
| 🔴 | Delete the "Untitled / Page" placeholder section | Immediate |
| 🟠 | Consolidate duplicate persona articles into single canonical articles with role callouts | Short-term |
| 🟠 | Flatten URL hierarchy to 3 levels max | Short-term |
| 🟠 | Add "Last updated" dates to all articles | Short-term |
| 🟠 | Enable article helpfulness ratings | Short-term |
| 🟠 | Embed tutorial videos inline instead of linking externally | Short-term |
| 🟠 | Add "Related articles" footer to every article | Short-term |
| 🟠 | Create a unified "Getting Started" track | Short-term |
| 🟠 | Add status page link to the site header | Short-term |
| 🟡 | Add GIFs/screen recordings for all UI-interaction articles | Medium-term |
| 🟡 | Native-English copyedit of all FAQ titles and article headings | Medium-term |
| 🟡 | Build a Troubleshooting section and a Billing & Plans section | Medium-term |
| 🟡 | Add FAQ schema markup for SEO rich results | Medium-term |
| 🟡 | Publish a public changelog | Medium-term |
| 🟡 | Decide and implement a localization strategy (FR/EN) | Medium-term |

---

## 1. Homepage & First Impression

### 🔴 [CRITICAL] Create a proper help center homepage
- [ ] The root URL (`/`) currently lands on a product description page titled "Video" with marketing copy and a compatibility table.
- [ ] Build a proper help center homepage with:
  - [ ] Prominent centered search bar (hero element)
  - [ ] Human greeting: "How can we help?"
  - [ ] Placeholder text modeling real queries (e.g. "How do I send an invitation by SMS?")
  - [ ] Search must be the largest, most prominent element, centered and above the fold.

### 🟠 [HIGH] Add quick-access topic chips
- [ ] No one-click shortcut to high-frequency topics exists.
- [ ] Add 6–10 pinned topic chips below the search bar:
  - First login
  - Send an invitation
  - Camera/mic issue
  - Change my password
  - Contact support

### 🟠 [HIGH] Add "What's new" / changelog section
- [ ] No release notes or changelog is visible on the homepage.
- [ ] Add a release notes / changelog section surfacing the 3–5 most recent product changes.

### 🟠 [HIGH] Add system status page link
- [ ] No system status link exists anywhere on the site.
- [ ] Add a status page link (header or homepage) to prevent incident tickets.

### 🟡 [MEDIUM] Add category card icons
- [ ] Category cards have no icons or visual differentiation; navigation is purely text-based.
- [ ] Add icons or illustrations per product/section card to accelerate scanning.

---

## 2. Information Architecture

### 🔴 [CRITICAL] Flatten URL hierarchy to ≤3 levels
- [ ] Many articles sit at depth 5: `/{product}/for-{persona}/{feature-group}/{sub-group}/{article}`
- [ ] Example given: `…/create-a-ticket-send-an-invitation/create-a-ticket-quick-invitation-by-email-and-or-sms`
- [ ] Flatten to 3 levels max: **Product → Task group → Article**
- [ ] Merge or eliminate intermediate index pages.

### 🔴 [CRITICAL] Eliminate massive content duplication across personas
- [ ] The same ~68–92 articles are copied verbatim under `for-administrators`, `for-agents`, `for-guests`, and `help-desk` for each product.
- [ ] This creates ~400+ duplicate pages, maintenance hell, and SEO cannibalization.
- [ ] Adopt a **single-article-with-role-callouts** model:
  - Write one article per task
  - Use callout blocks (e.g. "Admins only", "Not available for guests") to differentiate.
  - Or use conditional content blocks if GitBook supports them.

### 🔴 [CRITICAL] Create a dedicated "Getting Started" track
- [ ] No clear starting point for new users; no "Start here" section.
- [ ] Create a "Getting Started" guide per persona (or a single unified one).
- [ ] Make it the **first item** in navigation.

### 🟠 [HIGH] Rename persona-role labels to task-oriented language
- [ ] Top-level sections are named `for-administrators`, `for-agents`, `for-guests` — product-internal role labels.
- [ ] Rename to task-oriented labels, e.g.:
  - "Set up and administer your account"
  - "Run a video assistance session"
  - "Join a session as a guest"

### 🟠 [HIGH] Unify parallel product silos under single navigation
- [ ] Three separate product documentation spaces (Video Assistance, Embed, Multi-participant) exist as parallel silos.
- [ ] No unified navigation or cross-product search.
- [ ] Unify under a single top-level navigation with a **product selector** (top tab or dropdown).

### 🟠 [HIGH] Create a standalone "Troubleshooting" section
- [ ] No dedicated top-level "Troubleshooting" section exists.
- [ ] Troubleshooting articles are buried inside feature categories or in the FAQ.
- [ ] Create a standalone "Troubleshooting" section grouping all "I cannot…" and "Why is…" articles.

### 🟠 [HIGH] Create a top-level "Billing & Plans" section
- [ ] Billing & subscription articles are buried inside FAQ inside a persona section.
- [ ] This is one of the highest-urgency query types.
- [ ] Create a top-level "Billing & Plans" section, always reachable in one click from the homepage.

### 🟡 [MEDIUM] Standardize all URL paths to English
- [ ] The Multi-participant section uses `/pour-les-administrateurs/` and `/pour-les-agents/` while all other sections use English paths.
- [ ] Standardize all URL paths to English.
- [ ] Migrate French URLs with **301 redirects**.

### 🟡 [MEDIUM] Remove placeholder content
- [ ] An untitled section (`## Untitled`) containing a single article called `[Page]` is publicly published.
- [ ] Delete or replace the placeholder content immediately.

### 🟡 [MEDIUM] Fix or remove stub FAQ section
- [ ] Top-level "FAQ" section currently contains only **1 stub article**.
- [ ] Either build it out into a useful landing destination, or remove it and merge FAQ content into the Troubleshooting section.

### 🟡 [MEDIUM] Add version/edition selector (if applicable)
- [ ] No content version toggle for product tiers or deployment modes (e.g. Cloud vs. self-hosted, or different subscription tiers).
- [ ] Add a version/edition selector if the product has meaningfully different behavior across tiers.

---

## 3. Article Structure & Writing

### 🟠 [HIGH] Enable "Last updated" dates on all articles
- [ ] No "Last updated" date appears on any article.
- [ ] GitBook supports this natively — enable it globally or per-article.

### 🟠 [HIGH] Enable "Was this article helpful?" ratings
- [ ] No rating widget or feedback signal is collected on article quality.
- [ ] Enable GitBook's built-in reactions or add a thumbs up/down widget on every article.
- [ ] Review articles below **70% satisfaction** quarterly.

### 🟠 [HIGH] Add "Related articles" section to every article
- [ ] No "Related articles" section at the bottom of articles (only sporadic "More tutorials" links).
- [ ] Add a "Related articles" section (3–5 links) at the bottom of every article.

### 🟠 [HIGH] Fix or merge index/stub pages
- [ ] Many articles are index/stub pages containing only a list of child links and a single screenshot (e.g. "Create a ticket & send an invitation", "Start a video assistance").
- [ ] These provide no value as standalone destinations.
- [ ] Either:
  - Merge their content into the first child article, or
  - Add a meaningful introduction explaining the context, prerequisites, and what the user will accomplish.

### 🟡 [MEDIUM] Add "Before you begin" prerequisites block
- [ ] No prerequisites section in procedural articles.
- [ ] Example: "Log in to the Apizee portal for the first time" doesn't state what the user must have received before starting.
- [ ] Add a prerequisites block to any procedural article where prior conditions exist.

### 🟡 [MEDIUM] Add "In this article" table of contents for long articles
- [ ] No article-level table of contents for longer articles.
- [ ] Example: the compatibility/browser support article is extremely long with no anchor navigation.
- [ ] Add an "In this article" jump-link list at the top of any article exceeding **500 words**.

### 🟡 [MEDIUM] Standardize article titles to second person or imperative
- [ ] Inconsistent use of second-person voice.
- [ ] Most articles use "you", but FAQ titles use first person: "I do not manage to join…", "I forgot my password…"
- [ ] Rewrite FAQ titles to second person or imperative:
  - "Can't join the session?"
  - "Reset your password"
  - "Add a user to your account"

### 🟡 [MEDIUM] Fix garbled product name in FAQ title
- [ ] The FAQ landing page reads: "Here are all the Frequently Asked Questions about: Diag Help Des****k."
- [ ] Fix the FAQ title text immediately — this reads as broken content to every user.

### 🟡 [MEDIUM] Audit and fix broken image references
- [ ] "Share a screen" references `../../.gitbook/assets/tip.png` — a relative path that will not resolve correctly in the published GitBook environment.
- [ ] Audit all articles for broken relative image paths and replace with correct relative paths (GitBook mono-repo resolution) or absolute CDN paths.

### 🟡 [MEDIUM] Add meta descriptions to all articles
- [ ] No meta description appears to be configured on articles.
- [ ] GitBook supports custom meta descriptions via YAML frontmatter.
- [ ] Write a meta description for every article completing the sentence: "This article explains how to…"

### 🟡 [MEDIUM] Add "Next steps" guidance at end of getting-started articles
- [ ] No "Next steps" guidance at the end of Getting Started articles.
- [ ] Users complete an article and are sent back to the homepage rather than guided forward.
- [ ] Add a "Next steps" section at the end of each onboarding/getting-started article.

---

## 4. Search

### 🟠 [HIGH] Evaluate AI-powered search layer
- [ ] GitBook's native search is the only search mechanism — no synthesized answers from multiple articles.
- [ ] Standard for B2B SaaS help centers is now AI search (Intercom Fin, Notion AI, Slack Agentforce).
- [ ] Integrate an AI search layer:
  - GitBook's AI search feature (if available), or
  - A third-party like Inkeep or Kapa.ai
- [ ] Must return synthesized answers, not just a list of links.

### 🟠 [HIGH] Configure synonym/misspelling mapping
- [ ] No synonym/misspelling mapping is configured.
- [ ] Users searching for "call", "visio", "vidéo", "conference", "camera" need to reach the same articles.
- [ ] Configure a synonym dictionary in whatever search tool is used.

### 🟡 [MEDIUM] Customize zero-result page
- [ ] Zero-result behavior is not customized.
- [ ] Validate that GitBook's default zero-result state offers:
  - Reformulated suggestions
  - Popular articles
  - A direct "Contact support" link
- [ ] If not: customize the zero-result page to show popular articles and a prominent contact support option.

### 🟡 [MEDIUM] Set search placeholder text to a realistic query
- [ ] Search placeholder text is generic (GitBook default).
- [ ] Set placeholder text to a realistic example query, e.g. "How do I send an invitation by SMS?"

---

## 5. Visual Content & Media

### 🟠 [HIGH] Embed tutorial videos inline
- [ ] Videos are linked externally, not embedded.
- [ ] "Share a screen" ends with "Watch the tutorial" as an external link — every clicker leaves the help center.
- [ ] Embed all tutorial videos **inline** within the article using GitBook native video embeds.

### 🟡 [MEDIUM] Add annotated GIFs / screen recordings for UI interactions
- [ ] Articles describe multi-step UI interactions in text only.
- [ ] Example: "On the right-hand side, click the Screen sharing button" — a 5-second GIF would outperform 3 paragraphs of navigation instructions.
- [ ] Add annotated GIFs or short screen recordings for every article that involves clicking through the product UI.

### 🟡 [MEDIUM] Audit and update screenshot freshness
- [ ] Screenshot freshness cannot be verified.
- [ ] The compatibility table references browser versions (Chrome v45+, Firefox v46+) suggesting screenshots may be years out of date.
- [ ] Audit all screenshots per product release.
- [ ] Assign screenshot ownership per product area.
- [ ] Update the browser compatibility table to current versions.

### 🟡 [MEDIUM] Add annotated diagrams for conceptual topics
- [ ] Topics like "User roles", "About Apizee solutions", and permission models are described in text/tables only.
- [ ] Create annotated diagrams for at minimum:
  - User roles / permissions model
  - Product architecture overview
  - Session lifecycle flow

### 🟡 [MEDIUM] Build a structured learning track / academy
- [ ] No guided course for users who want to go from zero to proficient.
- [ ] Build at minimum a "Getting Started" learning path linking **5–8 articles in sequence** per persona, with progress indication.

---

## 6. Navigation & Discoverability

### 🟠 [HIGH] Add "Popular in this category" surface on landing pages
- [ ] No signal about which articles are most read within a category.
- [ ] Add "Most read in this section" chips or a ranked list at the top of each category landing page.

### 🟡 [MEDIUM] Add cross-product article tagging
- [ ] Articles relevant to multiple products or personas appear only in one place (e.g. browser compatibility, permission model).
- [ ] Tag cross-cutting articles to appear in all relevant sections (e.g. "Troubleshooting" AND the relevant feature category).

### 🟡 [MEDIUM] Validate breadcrumbs and flatten hierarchy
- [ ] With ~5-level deep URL hierarchy, breadcrumbs may display confusing intermediate index pages.
- [ ] Verify breadcrumb rendering.
- [ ] Flatten the hierarchy so breadcrumbs remain readable.

### 🟡 [MEDIUM] Group sidebar into collapsible sub-sections
- [ ] Sidebar is very long (~90 articles per persona section) and hard to scan.
- [ ] Group sidebar items into collapsible sub-sections to reduce cognitive load and surface current section context.

---

## 7. Tone & Voice

### 🟠 [HIGH] Native-English copyedit pass
- [ ] Awkward, non-native English phrasing in several titles and body text.
- [ ] Examples:
  - "I do not manage to join the video assistance" → "Can't join a video session?"
  - "people can't see/hear me" is idiomatic but "I do not have the sound notifications" is not.
  - "Choose a different password that you do not use for another Website" (unusual capitalization)
- [ ] Conduct a native-English copyedit pass across all article titles and FAQ items.
- [ ] Rewrite FAQ titles to natural second-/third-person or imperative forms.

### 🟡 [MEDIUM] Create and enforce a terminology glossary
- [ ] Same role called "requester," "guest," and implied to be the same as "user" in different articles.
- [ ] Same action described differently between product sections.
- [ ] Create a terminology glossary.
- [ ] Define once (e.g. in a "Getting Started" article): what is an **agent**, a **guest**, a **requester**, a **ticket**, a **session**.
- [ ] Audit all articles for consistency against the glossary.

### 🟡 [MEDIUM] Rewrite passive/hedging constructions to direct active voice
- [ ] Examples:
  - "This option may depend on your Web browser" → "This option varies by browser."
  - "Of course, and for security reasons, it is up to the administrator to choose the way…" → "Choose how to share login credentials with your users."

---

## 8. Support Escalation & Self-Service Completion

### 🟠 [HIGH] Build a visible tiered escalation model
- [ ] No visible path from: search failed → AI answer → community → ticket → chat.
- [ ] Only support contact is buried in the FAQ as "How to contact the Support Team."
- [ ] Build a visible escalation flow:
  - After failed search, surface an AI chatbot answer
  - Link to community (if one exists)
  - Ticket submission form
  - Response time estimate

### 🟠 [HIGH] Add response time expectation on contact support page
- [ ] No response time expectation shown when directing users to submit a ticket.
- [ ] Add "We typically respond within X hours" on the contact support page/article.

### 🟡 [MEDIUM] Link to a community forum
- [ ] No community forum linked from the help center.
- [ ] Peer support absorbs significant ticket volume and generates SEO-rich content.
- [ ] Add a community link (Slack, Discord, or forum) prominently in the navigation and on zero-result pages.

### 🟡 [MEDIUM] Add feature request / upvote mechanism
- [ ] When users hit a "this feature doesn't exist yet" dead end, they have nowhere to go.
- [ ] Link to a public roadmap or feature request board (Canny, Productboard, or native GitBook feedback) from relevant dead-end pages.

---

## 9. Trust & Transparency

### 🟠 [HIGH] Publish a public changelog / release notes
- [ ] No public changelog or release notes exist.
- [ ] Users have no way to discover new features or verify whether the documentation reflects the current product version.
- [ ] Publish a changelog section updated with every product release, and link it from the homepage.

### 🟠 [HIGH] Address "apizeelegacy" domain name confusion
- [ ] The domain `apizeelegacy.gitbook.io` signals outdated documentation to every user.
- [ ] This erodes trust immediately, especially for new users.
- [ ] Clarify prominently on the homepage which product version this documentation covers, and link to the current documentation if one exists.
- [ ] If this is the primary documentation, plan migration to a non-legacy URL.

### 🟡 [MEDIUM] Add article author / team attribution
- [ ] Articles are anonymous.
- [ ] Add "Maintained by the [Product/Support] team" or author attribution per article.
- [ ] This signals human accountability and active maintenance.

### 🟡 [MEDIUM] Display article counts per section
- [ ] Users can't assess how mature a section is before diving in (unlike Intercom's "18 authors, 132 articles" model).
- [ ] Display article counts per section on category landing pages.

### 🟡 [MEDIUM] Create a public "Known Issues" page
- [ ] Recurring bugs or platform issues cause repeated tickets.
- [ ] Create a public "Known Issues" page with current workarounds.
- [ ] Link from the homepage and from relevant troubleshooting articles.

### 🟡 [MEDIUM] Add status page link to header
- [ ] No status page link anywhere in the site.
- [ ] During an outage, this is the highest-impact single link the help center can provide.
- [ ] Add a status page link in the site header or homepage (green/yellow/red indicator preferred).

---

## 10. SEO & Findability

### 🟠 [HIGH] Flatten URL structure to 2–3 segments
- [ ] Extremely deep URL paths hurt SEO.
- [ ] Example: `…/create-a-ticket-send-an-invitation/create-a-ticket-quick-invitation-by-email-and-or-sms` is 6 segments deep.
- [ ] Search engines deprioritize deep URLs; users can't remember or share them.
- [ ] Flatten to **2–3 segments max**.
- [ ] Example target: `/send-invitation-email-sms`

### 🟠 [HIGH] Consolidate canonical articles and set 301 redirects
- [ ] Massive content duplication across personas creates SEO cannibalization.
- [ ] 4 near-identical versions of the same ~90 articles split link equity and confuse search engines.
- [ ] Consolidate to single canonical articles with role-specific callouts.
- [ ] Set **301 redirects** from all duplicate URLs to the canonical URL.

### 🟡 [MEDIUM] Add FAQ schema markup (JSON-LD)
- [ ] No FAQ schema markup is configured.
- [ ] The FAQ section is a natural candidate for Google rich results / accordion display in SERPs, dramatically increasing CTR.
- [ ] Add FAQ schema markup to all FAQ articles and to any article with a Q&A structure.

### 🟡 [MEDIUM] Add explicit internal links within articles
- [ ] Internal linking between related articles is sparse.
- [ ] Only a few "More tutorials" links observed.
- [ ] Add explicit internal links within article body text wherever a related concept is mentioned, and add "Related articles" footer sections.

### 🟡 [MEDIUM] Verify crawlability and indexing
- [ ] Cannot verify whether the help center is fully crawlable.
- [ ] GitBook instances sometimes unintentionally restrict crawlers via `robots.txt` or `noindex` tags.
- [ ] Verify crawlability in Google Search Console.
- [ ] Ensure all published articles are indexed.

---

## 11. Internationalization

### 🟠 [HIGH] Decide and implement a localization strategy
- [ ] Documentation is English-only despite Apizee being a French company with likely significant French-speaking user base.
- [ ] The Multi-participant section uses French URL slugs (`pour-les-administrateurs`) suggesting French content existed or was started but not completed.
- [ ] Decide on a clear strategy:
  - Either fully commit to bilingual (FR/EN) docs with proper `hreflang` tags and locale subpaths (`/fr/`), or
  - Remove the French URL segments and 301-redirect them.

### 🟡 [MEDIUM] Add language selector if multilingual
- [ ] No language selector visible anywhere on the site.
- [ ] Add a visible language selector on every page if multiple language versions exist or are planned.

### 🟡 [MEDIUM] Localize dates and system requirements
- [ ] Dates like "01/03/2026" are ambiguous across locales.
- [ ] Use unambiguous date formats (e.g. "1 March 2026" or ISO 8601) throughout.

---

## 12. Metrics & Continuous Improvement

### 🟠 [HIGH] Enable and review article helpfulness ratings
- [ ] No article helpfulness rating is collected.
- [ ] Without this signal, there is no data-driven way to identify articles needing rewriting.
- [ ] Enable ratings on every article (GitBook supports reactions).
- [ ] Set a **quarterly review cadence** for articles below **70% positive**.

### 🟠 [HIGH] Set up search analytics and zero-result monitoring
- [ ] No evidence of search query logging or zero-result monitoring.
- [ ] The top 50 zero-result queries represent the documentation backlog.
- [ ] Set up search analytics (GitBook Insights or a third-party like Datadog or Mixpanel).
- [ ] Review zero-result queries **monthly**.

### 🟡 [MEDIUM] Establish lightweight title testing process
- [ ] No A/B testing infrastructure for article titles.
- [ ] Title changes are the highest-leverage SEO intervention.
- [ ] Track CTR per article in Google Search Console.
- [ ] Test alternate titles for the **top 20 most-searched articles**.

### 🟡 [MEDIUM] Build a support agent feedback loop
- [ ] Support agents know which docs are wrong or missing; there is no way for them to flag articles directly.
- [ ] Add an "Is something wrong with this article?" link on every page that routes to the docs team.
- [ ] Establish a **quarterly support agent review**.
