"""
Question bank: 10 questions per session for any job role and interview type.
Uses role text + keywords to personalize generic professional templates.
"""
import hashlib
import re
from typing import List

INTERVIEW_TYPES = [
    "technical",
    "behavioral",
    "hr",
    "leadership",
    "sales_client",
    "case_problem_solving",
    "operations",
    "product_ux",
    "finance_legal",
    "general_mixed",
]

# Templates: (question_text, focus_tag)
# {role} = job title, {company_context} = optional snippet from role

TECHNICAL = [
    ("Describe the core technical stack or tools you would expect to use daily as a {role}. How do you stay current?", "technical_depth"),
    ("Walk through how you would debug a critical production issue affecting users in a {role} capacity.", "problem_solving"),
    ("Explain a complex technical concept relevant to {role} to a non-technical stakeholder.", "communication"),
    ("How do you balance code quality, deadlines, and technical debt in projects related to {role}?", "judgment"),
    ("Describe a time you optimized performance or reliability in a system relevant to your domain.", "experience"),
    ("What metrics would you track to measure success in your work as a {role}?", "metrics"),
    ("How do you approach testing and validation for deliverables in your field?", "quality"),
    ("Describe your experience with version control, CI/CD, or collaboration tools in technical work.", "tools"),
    ("What is a recent technical challenge you solved, and what was your approach?", "experience"),
    ("Where do you see the biggest technical risks in projects typical for a {role}, and how do you mitigate them?", "risk"),
]

BEHAVIORAL = [
    ("Tell me about a time you faced a tight deadline as a {role}. What did you prioritize?", "star"),
    ("Describe a conflict with a colleague or stakeholder and how you resolved it.", "collaboration"),
    ("Give an example of feedback you received that was hard to hear. What did you change?", "growth"),
    ("Describe a failure or mistake in your professional life and what you learned.", "resilience"),
    ("Tell me about a time you had to learn something new quickly for your role.", "adaptability"),
    ("How do you handle competing priorities from multiple stakeholders?", "organization"),
    ("Describe a situation where you showed leadership without formal authority.", "influence"),
    ("Tell me about a time you went above expectations for a customer or user.", "ownership"),
    ("How do you stay motivated during repetitive or difficult phases of work?", "motivation"),
    ("Describe a time you helped onboard or mentor someone.", "teamwork"),
]

HR = [
    ("Why are you interested in this type of position and how does it align with your career goals?", "motivation"),
    ("What kind of work environment helps you do your best work?", "culture_fit"),
    ("How do you balance work and personal well-being?", "wellbeing"),
    ("Describe your ideal manager and how you like to receive feedback.", "expectations"),
    ("What are your salary or role expectations (conceptually), and what matters most to you in an offer?", "expectations"),
    ("How do you handle stress and pressure in demanding periods?", "stress"),
    ("What diversity and inclusion mean to you in a workplace?", "values"),
    ("Where do you see yourself in three to five years?", "career"),
    ("What would you like us to know about you that is not on your resume?", "personality"),
    ("Why should we hire you for this {role} role specifically?", "closing"),
]

LEADERSHIP = [
    ("How do you set vision and priorities for a team working on {role}-related outcomes?", "vision"),
    ("Describe how you delegate and hold people accountable.", "management"),
    ("Tell me about a time you had to deliver bad news to your team or leadership.", "communication"),
    ("How do you develop and retain talent in your area?", "people"),
    ("How do you measure team success beyond individual outputs?", "metrics"),
    ("Describe a time you had to reorganize or rescope work under uncertainty.", "change"),
    ("How do you balance stakeholder demands with team capacity?", "judgment"),
    ("What is your approach to hiring for roles like {role}?", "hiring"),
    ("How do you foster psychological safety while driving results?", "culture"),
    ("Tell me about a strategic decision you led and its outcome.", "strategy"),
]

SALES_CLIENT = [
    ("How do you build trust quickly with a new client or account in a {role} context?", "rapport"),
    ("Walk through your approach to handling a price objection.", "negotiation"),
    ("Describe a lost deal or unhappy client and what you learned.", "resilience"),
    ("How do you qualify prospects to avoid wasting time?", "process"),
    ("How do you balance short-term sales targets with long-term relationships?", "strategy"),
    ("Tell me about a time you turned around a difficult customer situation.", "service"),
    ("How do you prepare for a high-stakes demo or pitch?", "preparation"),
    ("What CRM or pipeline habits do you use to stay organized?", "tools"),
    ("How do you collaborate with technical or product teams when selling?", "collaboration"),
    ("Describe your personal brand or approach to networking in your industry.", "networking"),
]

CASE = [
    ("How would you estimate demand or resource needs for a new initiative in {role}?", "estimation"),
    ("A key metric dropped 20% week over week. How do you investigate?", "analysis"),
    ("How would you prioritize five urgent requests with limited capacity?", "prioritization"),
    ("Design a lightweight process to reduce errors in a repeatable workflow.", "process"),
    ("How would you decide whether to build vs buy vs partner for a capability?", "decision"),
    ("Describe how you would break down a vague goal into actionable steps.", "planning"),
    ("What data would you need before recommending a major change?", "data"),
    ("How do you handle ambiguity when requirements are unclear?", "ambiguity"),
    ("Walk through a root cause analysis you performed in a past role.", "rca"),
    ("How would you communicate trade-offs to executives in one page?", "communication"),
]

OPERATIONS = [
    ("How do you ensure SLAs in a high-volume operational role like {role}?", "sla"),
    ("Describe your approach to process documentation and continuous improvement.", "process"),
    ("How do you handle escalations and incident communication?", "incidents"),
    ("What KPIs do you use to monitor operational health?", "metrics"),
    ("Tell me about a time you reduced cost or waste in a process.", "efficiency"),
    ("How do you coordinate across teams for end-to-end delivery?", "coordination"),
    ("Describe your experience with vendor or third-party management.", "vendors"),
    ("How do you balance speed with quality in operational execution?", "speed_quality"),
    ("What tools or automation have you used in operations?", "tools"),
    ("How do you plan for peak load or seasonal spikes?", "capacity"),
]

PRODUCT_UX = [
    ("How do you discover what users really need in a {role} context?", "discovery"),
    ("Describe how you prioritize a backlog when everything seems important.", "prioritization"),
    ("How do you balance user needs, business goals, and technical constraints?", "tradeoffs"),
    ("Tell me about a feature or experience you shipped and how you measured impact.", "impact"),
    ("How do you approach usability testing or user research?", "research"),
    ("How do you work with engineering and design when opinions conflict?", "collaboration"),
    ("Describe a time you said no to a stakeholder request.", "judgment"),
    ("What is your framework for writing requirements or acceptance criteria?", "requirements"),
    ("How do you stay informed about competitors and market trends?", "market"),
    ("How do you handle roadmap changes mid-cycle?", "agility"),
]

FINANCE_LEGAL = [
    ("How do you ensure accuracy and compliance in work typical for a {role}?", "compliance"),
    ("Describe your experience with reporting, audits, or controls.", "controls"),
    ("How do you communicate financial or legal risk to non-experts?", "communication"),
    ("Tell me about a time you identified a discrepancy or error. What did you do?", "integrity"),
    ("How do you balance thoroughness with deadlines in regulated environments?", "balance"),
    ("What tools or systems do you use for analysis and documentation?", "tools"),
    ("How do you stay updated on regulatory or accounting changes?", "learning"),
    ("Describe a complex analysis or contract review you led.", "depth"),
    ("How do you handle confidential information?", "ethics"),
    ("How do you approach forecasting or scenario planning?", "forecasting"),
]

GENERAL_MIXED = [
    ("Summarize your background and how it prepares you for {role}.", "overview"),
    ("What are your strongest professional skills, and where are you growing?", "self_awareness"),
    ("Describe a typical project lifecycle in your experience.", "process"),
    ("How do you learn new domains or tools when required?", "learning"),
    ("What motivates you in your day-to-day work?", "motivation"),
    ("How do you give and receive feedback?", "communication"),
    ("Tell me about a time you influenced a decision without authority.", "influence"),
    ("What questions do you have for us about the role or team?", "closing"),
    ("How do you document and share knowledge with others?", "collaboration"),
    ("Describe a time you improved something at work beyond your scope.", "initiative"),
]

TYPE_MAP = {
    "technical": TECHNICAL,
    "behavioral": BEHAVIORAL,
    "hr": HR,
    "leadership": LEADERSHIP,
    "sales_client": SALES_CLIENT,
    "case_problem_solving": CASE,
    "operations": OPERATIONS,
    "product_ux": PRODUCT_UX,
    "finance_legal": FINANCE_LEGAL,
    "general_mixed": GENERAL_MIXED,
}


def _normalize_role(role: str) -> str:
    r = (role or "").strip()
    if not r:
        return "professional"
    return r[:120]


def _keywords_from_role(role: str) -> List[str]:
    stop = {
        "a", "an", "the", "and", "or", "for", "in", "on", "at", "to", "of", "with",
        "is", "are", "as", "by", "i", "ii", "iii", "jr", "sr", "level", "entry",
    }
    words = re.findall(r"[a-zA-Z0-9+.#]+", role.lower())
    return [w for w in words if w not in stop and len(w) > 1][:8]


def build_questions(job_role: str, interview_type: str) -> List[dict]:
    """
    Returns exactly 10 questions with stable ids based on role+type hash.
    """
    it = (interview_type or "general_mixed").lower().strip()
    if it not in TYPE_MAP:
        it = "general_mixed"

    role = _normalize_role(job_role)
    role_display = role.title() if role else "Professional"
    kws = _keywords_from_role(job_role)
    kw_hint = ", ".join(kws[:3]) if kws else "your domain"

    # Optional second line for variety (not shown as separate question — woven into text)
    templates = TYPE_MAP[it]
    seed = hashlib.sha256(f"{role}|{it}".encode()).hexdigest()

    questions = []
    for i in range(10):
        t = templates[i % len(templates)]
        text = t[0].format(role=role_display, company_context=kw_hint)
        tag = t[1]
        qid = f"q-{seed[:8]}-{i+1}"
        questions.append({
            "id": qid,
            "index": i + 1,
            "text": text,
            "tag": tag,
        })
    return questions
