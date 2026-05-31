"""
Form Filler - AI reads resume dynamically to answer every question
Uses Groq instead of Ollama
"""

import asyncio
import json
import logging
import re
from playwright.async_api import async_playwright, Page
from groq_client import GroqClient

log = logging.getLogger("FormFiller")

ATS_PATTERNS = {
    "google_forms": "docs.google.com/forms",
    "workday":      "myworkdayjobs.com",
    "greenhouse":   "boards.greenhouse.io",
    "lever":        "jobs.lever.co",
    "ashby":        "ashbyhq.com",
    "breezy":       "breezy.hr",
}


class FormFiller:
    def __init__(self, resume_text: str, groq_config: dict):
        self.resume       = resume_text
        self.answer_cache = {}
        self.job_context  = ""
        self.groq         = GroqClient(groq_config)
        self.last_error   = ""

    async def apply(self, url: str, job_context: str = "") -> tuple[bool, str]:
        self.answer_cache = {}
        self.job_context  = job_context
        self.last_error   = ""
        ats = self._detect_ats(url)
        log.info(f"Detected ATS: {ats} for {url}")

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    viewport={"width": 1280, "height": 900},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                )
                page = await context.new_page()
                await page.goto(url, timeout=60000, wait_until="domcontentloaded")

                if ats == "google_forms":
                    success = await self._fill_google_form(page)
                elif ats == "workday":
                    success = await self._fill_workday(page)
                elif ats in ("greenhouse", "lever", "ashby", "breezy"):
                    success = await self._fill_generic_ats(page)
                else:
                    success = await self._fill_ai_guided(page)

                await browser.close()
                if success:
                    return True, "Submitted successfully"
                if not self.last_error:
                    self.last_error = f"Form not completed ({ats} ATS)"
                return False, self.last_error

        except Exception as e:
            self.last_error = str(e)[:500]
            log.error(f"Form filler error: {e}")
            return False, self.last_error

    # ─── Core AI Answer Engine ────────────────────────────────────────────────

    async def ask(self, question: str, options: list = None) -> str:
        cache_key = question.strip().lower()
        if cache_key in self.answer_cache:
            return self.answer_cache[cache_key]

        options_text = ""
        if options:
            options_text = "\nAvailable options:\n" + "\n".join(f"- {o}" for o in options)

        prompt = f"""You are filling a job application form on behalf of a candidate.
Use ONLY the information from their resume below to answer. Do not make up anything not in the resume.
If the resume doesn't have the answer, use the most reasonable professional default.

=== CANDIDATE RESUME ===
{self.resume}
========================

Job context:
{self.job_context[:500] if self.job_context else "Not specified"}

Form question: "{question}"
{options_text}

Rules:
- Answer ONLY with the value to fill in, nothing else
- No explanations, no preamble
- If choosing from options, return the exact option text
- For yes/no questions, answer Yes or No
- For salary, say "Negotiable" unless resume mentions specific expectation
- For notice period, default "2 weeks"
- Keep answers concise unless cover letter or essay

Answer:"""

        try:
            answer = await self.groq.generate(prompt, temperature=0.1)
            self.answer_cache[cache_key] = answer
            return answer
        except Exception as e:
            log.error(f"AI answer failed: {e}")
            return ""

    async def generate_cover_letter(self, job_description: str = "") -> str:
        prompt = f"""Write a professional cover letter for this job application.

=== CANDIDATE RESUME ===
{self.resume}
========================

Job posting / context:
{job_description[:1000] if job_description else "Not specified"}

Write a 3-paragraph cover letter:
1. Opening: express interest, mention the role
2. Middle: highlight 2-3 most relevant skills/experiences from resume
3. Closing: call to action

Keep it under 250 words. Professional but warm tone. No generic filler phrases."""

        try:
            return await self.groq.generate(prompt, temperature=0.4)
        except Exception as e:
            log.error(f"Cover letter generation failed: {e}")
            return ""

    # ─── Google Forms ─────────────────────────────────────────────────────────

    async def _fill_google_form(self, page: Page) -> bool:
        log.info("Filling Google Form...")

        for page_num in range(20):
            await page.wait_for_timeout(1500)
            questions = await self._get_google_questions(page)
            if not questions:
                break

            for q in questions:
                await self._fill_google_question(page, q)
                await page.wait_for_timeout(300)

            submit_btn = page.locator('div[role="button"]:has-text("Submit")')
            next_btn   = page.locator('div[role="button"]:has-text("Next")')

            if await submit_btn.count() > 0:
                await submit_btn.click()
                await page.wait_for_timeout(2000)
                log.info("Google Form submitted!")
                return True
            elif await next_btn.count() > 0:
                await next_btn.click()
                log.info(f"Google Form page {page_num + 2}...")
            else:
                break

        return False

    async def _get_google_questions(self, page: Page) -> list:
        questions = []
        items = await page.query_selector_all('div[role="listitem"]')

        for item in items:
            heading = await item.query_selector('div[role="heading"]')
            if not heading:
                continue
            q_text = await heading.inner_text()

            text_input = await item.query_selector('input[type="text"], textarea')
            radios     = await item.query_selector_all('div[role="radio"]')
            checkboxes = await item.query_selector_all('div[role="checkbox"]')
            dropdown   = await item.query_selector('div[role="combobox"]')

            if text_input:
                questions.append({"text": q_text, "type": "text", "el": text_input})
            elif radios:
                labels = [await r.inner_text() for r in radios]
                questions.append({"text": q_text, "type": "radio", "el": radios, "options": labels})
            elif checkboxes:
                labels = [await c.inner_text() for c in checkboxes]
                questions.append({"text": q_text, "type": "checkbox", "el": checkboxes, "options": labels})
            elif dropdown:
                questions.append({"text": q_text, "type": "dropdown", "el": dropdown})

        return questions

    async def _fill_google_question(self, page: Page, q: dict):
        q_text = q["text"]

        if any(kw in q_text.lower() for kw in ["cover letter", "why do you want", "tell us about yourself"]):
            answer = await self.generate_cover_letter(self.job_context)
        else:
            answer = await self.ask(q_text, q.get("options"))

        try:
            if q["type"] == "text":
                await q["el"].fill(answer)

            elif q["type"] == "radio":
                matched = False
                for option_el in q["el"]:
                    label = await option_el.inner_text()
                    if answer.lower() in label.lower() or label.lower() in answer.lower():
                        await option_el.click()
                        matched = True
                        break
                if not matched:
                    await q["el"][0].click()

            elif q["type"] == "checkbox":
                await q["el"][0].click()

            elif q["type"] == "dropdown":
                await q["el"].click()
                await page.wait_for_timeout(400)
                opt = page.locator(f'li:has-text("{answer}")')
                if await opt.count() > 0:
                    await opt.first.click()

        except Exception as e:
            log.warning(f"Could not fill '{q_text}': {e}")

    # ─── Workday ──────────────────────────────────────────────────────────────

    async def _fill_workday(self, page: Page) -> bool:
        log.info("Filling Workday...")
        apply_btn = page.locator('button:has-text("Apply"), a:has-text("Apply Now")')
        if await apply_btn.count() > 0:
            await apply_btn.first.click()
            await page.wait_for_timeout(2000)
        return await self._fill_ai_guided(page, max_steps=25)

    # ─── Generic ATS ──────────────────────────────────────────────────────────

    async def _fill_generic_ats(self, page: Page) -> bool:
        log.info("Filling generic ATS...")
        await self._fill_visible_fields(page)
        return await self._fill_ai_guided(page)

    # ─── AI-Guided Universal Filler ───────────────────────────────────────────

    async def _fill_ai_guided(self, page: Page, max_steps: int = 15) -> bool:
        for step in range(max_steps):
            await page.wait_for_timeout(1500)
            await self._fill_visible_fields(page)

            action = await self._next_action(page, step)
            log.info(f"Step {step+1}: {action['action']} → {action.get('target', '')}")

            if action["action"] == "submit":
                btn = page.locator(f'button:has-text("{action.get("target", "Submit")}")')
                if await btn.count() > 0:
                    await btn.first.click()
                    await page.wait_for_timeout(2000)
                    return True

            elif action["action"] == "click":
                target = action.get("target", "Next")
                btn = page.locator(f'button:has-text("{target}"), a:has-text("{target}")')
                if await btn.count() > 0:
                    await btn.first.click()

            elif action["action"] == "fill":
                selector = action.get("selector", "")
                question = action.get("question", "")
                answer   = await self.ask(question)
                if selector:
                    try:
                        await page.fill(selector, answer)
                    except Exception:
                        pass

            elif action["action"] in ("done", "failed"):
                if action["action"] == "failed":
                    self.last_error = action.get("reason", "Automation marked step as failed")
                return action["action"] == "done"

        self.last_error = f"Hit {max_steps}-step limit without submit confirmation"
        return False

    async def _fill_visible_fields(self, page: Page):
        inputs = await page.query_selector_all(
            'input[type="text"]:visible, input[type="email"]:visible, '
            'input[type="tel"]:visible, textarea:visible'
        )

        for inp in inputs:
            try:
                current = await inp.input_value()
                if current:
                    continue

                field_id    = await inp.get_attribute("id") or ""
                placeholder = await inp.get_attribute("placeholder") or ""
                aria_label  = await inp.get_attribute("aria-label") or ""
                name        = await inp.get_attribute("name") or ""

                label_text = ""
                if field_id:
                    label_el = await page.query_selector(f'label[for="{field_id}"]')
                    if label_el:
                        label_text = await label_el.inner_text()

                question = label_text or aria_label or placeholder or name
                if not question:
                    continue

                tag = await inp.evaluate("el => el.tagName")
                if tag == "TEXTAREA" and any(kw in question.lower() for kw in ["cover", "why", "about yourself", "motivation"]):
                    answer = await self.generate_cover_letter(self.job_context)
                else:
                    answer = await self.ask(question)

                if answer:
                    await inp.fill(answer)
                    await page.wait_for_timeout(200)

            except Exception:
                pass

    async def _next_action(self, page: Page, step: int) -> dict:
        """Text-based next action — no vision model needed"""
        # Check for submit button
        for submit_text in ["Submit Application", "Submit", "Apply", "Apply Now"]:
            btn = page.locator(f'button:has-text("{submit_text}")')
            if await btn.count() > 0:
                return {"action": "submit", "target": submit_text}

        # Check for next button
        for next_text in ["Next", "Continue", "Save and Continue", "Next Step"]:
            btn = page.locator(f'button:has-text("{next_text}")')
            if await btn.count() > 0:
                return {"action": "click", "target": next_text}

        # Check for success/confirmation
        content = await page.content()
        if any(kw in content.lower() for kw in ["thank you", "application submitted", "successfully applied"]):
            return {"action": "done", "target": ""}

        return {"action": "click", "target": "Next", "reason": "fallback"}

    def _detect_ats(self, url: str) -> str:
        for name, pattern in ATS_PATTERNS.items():
            if pattern in url:
                return name
        return "generic"