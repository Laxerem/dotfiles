---
name: text-style
description: Applies a specific authorial writing style for technical and semi-technical Russian-language texts. Use when writing changelogs, release notes, status updates, bot messages, or any structured prose where the author's voice and formatting conventions should be preserved. Covers structure, abstraction level, punctuation rhythm, emoji semantics, and the balance between formality and personality.
---

This skill defines how to write and format text in the author's voice. It is not a rigid template — it describes tendencies, patterns, and principles. Vary the structure where variation is natural. The single rule that cannot break: the text must feel written by a person, not assembled by a machine.

---

## Voice and Tone

The tone sits between technical and conversational — precise enough to be trusted, human enough to be readable. It doesn't perform professionalism. It doesn't hedge. It doesn't pad.

When the context is a bot message or a public-facing update, the register drops slightly: shorter sentences, direct address ("ты"), occasional dry humor. When it's a technical changelog, the register rises: named classes, HTTP methods, exact field names — but the sentences still breathe.

Personality surfaces through word choice, not decoration. A bug doesn't just "occur" — it "обнаружился драматичным образом". A bot "уверенно держался пару часов ☠️". These moments are rare and exact. Don't scatter them — let them land.

---

## Structure

Structure follows function. There is no one correct structure across all texts.

For **technical updates and changelogs**, a common pattern is:

1. A short problem framing ("Вступление" / "Введение") — past tense, describes what was wrong or missing before.
2. The solution or change — concise, present tense.
3. Technical specifics — endpoints, schemas, code identifiers, numbered steps.

This pattern is not mandatory. Sometimes the introduction is a single sentence. Sometimes it's skipped entirely and the text leads with the change. Sometimes problem and solution collapse into one statement. Let the content dictate.

For **public announcements and status updates**, structure is looser. Often a short narrative, then the practical takeaway, then a call to action. The narrative can carry a bit of drama if the situation warrants it.

For **bot UI messages** (greetings, prompts, profile views), the structure is list-heavy but not bureaucratic: grouped by theme, led by a short framing sentence, closed with a light personal touch.

---

## Introductions

When an introduction exists, it earns its place by answering: *why does this change matter?* It names the problem that existed before the fix, not the fix itself.

- Past tense for the old situation: "Ранее...", "В прошлой реализации...", "До текущего обновления..."
- 1–3 sentences. No more.
- No solution yet — just the gap or the failure.

The solution comes after, separately. This order — problem, then answer — is consistent and intentional.

---

## Abstraction Level

The introduction stays abstract. It describes behavior and consequences, not implementation.

The technical section goes specific: exact class names, endpoint paths, field names, HTTP methods — in code formatting. No softening with "something like" or "similar to". If you know the name, use it.

When both levels coexist in one text, the shift between them is clean. There's no blurring in the middle.

---

## Emoji

Emoji are semantic, not decorative.

In section headers, emoji signals the *type* of change:
- 🏗 — architectural change, refactor, reorganization
- ✨ — new feature or meaningful update
- 🛠 — fix, correction, patch
- 📱 — UI or client-side
- ⚙️ — technical internals, configuration

In running text, emoji appears occasionally and specifically — to mark tone (☠️ for something that failed badly), to punctuate a list item, or to close a message with personality. It does not appear in every sentence. When it appears, it means something.

In bot messages addressed to users, emoji is more present but still purposeful: it marks category (💫 for identity, ✨ for availability, 🚀 for forward motion). Not every line gets one.

---

## Formatting Conventions

**Bold** — for key concepts, category labels, important terms that deserve visual weight. In bullet lists, the subject of the bullet is often bolded.

`Backtick code` — for all technical identifiers without exception: class names, method names, field names, endpoint paths, status strings, variable names. If it's a thing in the code or API, it's in backticks.

```code blocks``` — for JSON schemas, HTTP response examples, multi-line code. Labeled when the format isn't obvious.

Lists — used when there are genuinely multiple parallel items. Not used to break up prose that should flow as prose. Bullet lists for unordered items; numbered lists when sequence matters.

Headers — used to separate meaningfully distinct sections within a longer text. Not used for single-section entries. An emoji in the header is normal.

---

## Sentence Rhythm

Sentences are short to medium. Long sentences exist when they need to — when a chain of cause and effect requires it, or when a clause would feel amputated on its own. But they don't accumulate.

Connective tissue is sparse and intentional: "К тому же", "Однако", "Так же" — used once or twice per section, not as filler between every point.

No throat-clearing openers. No "Таким образом" conclusions. A section ends when the content ends.

---

## What to Avoid

- Writing every entry with the same structure. Pattern recognition is fine; mechanical replication is not.
- Vague adjectives with no operational content ("качественный", "удобный", "простой") unless followed immediately by something concrete.
- Bullet lists that restate prose already written above them.
- Emoji on every line.
- Closing summaries that repeat the opening.
- Formal sign-offs on technical sections. (The bot messages have "С уважением, Diskay." — that's a specific voice for a specific character, not a general convention.)
- Hedging: "возможно", "в некотором роде", "своего рода" — cut them unless uncertainty is genuinely the point.
