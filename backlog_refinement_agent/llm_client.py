# backlog_refinement_agent/llm_client.py
from typing import Tuple
from openai import OpenAI

from .config import settings


client = OpenAI(api_key=settings.openai.api_key)

def is_vague_summary_with_llm(summary: str) -> tuple[bool, str]:
    if not summary or not isinstance(summary, str) or len(summary.strip()) < 5:
        return True, "Summary is too short to evaluate clearly."

    try:
        system_prompt = (
     "You are a senior product manager conducting a backlog refinement session. "
    "Your task is to evaluate a Jira story summary and determine whether it is clear, specific, and actionable "
    "based on standard Agile Product Development practices. "
    "Respond with the following format:\n\n"
    "Classification: [Vague or Clear]\n"
    "Explanation: [1 to 2 line reasoning]"
        )

        user_prompt = f"Summary: {summary.strip()}"

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # or gpt-4o if preferred
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=150,
            temperature=0
        )

        content = response.choices[0].message.content.strip()

        is_vague = any(keyword in content.lower() for keyword in ["vague", "unclear", "misleading"])
        return is_vague, content

    except Exception as e:
        print("⚠️ LLM summary evaluation failed:", e)
        return False, "LLM evaluation failed due to an error."    


def is_valid_acceptance_criteria_with_llm(description: str) -> tuple[bool, str]:
    if not description or not isinstance(description, str) or len(description.strip()) < 10:
        return True, "Description is too short to contain meaningful acceptance criteria."

    try:
        system_prompt = (
    "You are a senior product manager reviewing a Jira story description. "
    "Your task is to evaluate whether it contains clear and testable acceptance criteria, "
    "as typically required in Agile Product Development. "
    "Respond with the following format:\n\n"
    "Classification: [Complete or Incomplete]\n"
    "Explanation: [1 to 2 line reasoning]"
        )

        user_prompt = f"Description: {description.strip()}"

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=100,
            temperature=0
        )

        content = response.choices[0].message.content.strip()

        is_incomplete = any(term in content.lower() for term in ["incomplete", "missing", "unclear", "does not", "not present"])
        return is_incomplete, content

    except Exception as e:
        print("⚠️ LLM description evaluation failed:", e)
        return False, "LLM evaluation failed."


def suggest_acceptance_criteria_with_llm(summary: str, description: str) -> str:
    try:
        system_prompt = (
            "You are a senior product manager participating in a backlog refinement session. "
    "You are a senior product owner and your task is to review a Jira story's summary and description, and suggest clear, specific, and testable "
    "acceptance criteria based on Agile product development best practices.\n\n"
    "Start with the heading:\n"
    "Suggested Acceptance Criteria\n\n"
    "Then provide a bulleted list of acceptance criteria. "
        )

        user_prompt = f"""
Summary: {summary.strip()}

Description: {description.strip()}
"""

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=200,
            temperature=0.2
        )

        content = response.choices[0].message.content.strip()
        return content

    except Exception as e:
        print("⚠️ LLM acceptance criteria suggestion failed:", e)
        return "(Suggestion failed due to LLM error)"
