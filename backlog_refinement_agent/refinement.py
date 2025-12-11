# backlog_refinement_agent/refinement.py
from typing import Dict, Any, List, Tuple

from .llm_client import (
    is_vague_summary_with_llm,
    is_valid_acceptance_criteria_with_llm,
    suggest_acceptance_criteria_with_llm,
)


def extract_full_description(description_block):
    def extract_text_from_node(node):
        text = ""
        if "text" in node:
            text += node["text"]
        if "content" in node:
            for child in node["content"]:
                text += extract_text_from_node(child)
        return text

    description = ""
    if isinstance(description_block, dict) and "content" in description_block:
        for block in description_block["content"]:
            block_text = extract_text_from_node(block)
            if block.get("type") == "bulletList":
                # Add bullets for bullet list items
                for item in block.get("content", []):
                    item_text = extract_text_from_node(item).strip()
                    if item_text:
                        description += f"- {item_text}\n"
            else:
                if block_text.strip():
                    description += block_text + "\n"

    return description.strip()


def evaluate_story(story: Dict[str, Any], present_fields: List[str]) -> Tuple[List[str], Dict[str, str], str]:
    issues = []
    explanations = {}
    ac_suggestion = ""

    # --- Summary Analysis ---
    if "summary" in present_fields:
        summary = story.get("summary", "")
        if not summary.strip():
            explanations["summary"] = "Summary is empty or only whitespace."
        else:
            is_vague, explanation = is_vague_summary_with_llm(summary)
            if is_vague:
                # issues.append("Summary Analysis:\nVague or unclear summary")
                issues.append("Summary Analysis")
                explanations["summary"] = explanation

    # --- Description Analysis ---
    if "description" in present_fields:
        description = story.get("description", "")
        if not description.strip():
            # issues.append("Vague or unclear description")
            issues.append("Description Analysis")
            explanations["description"] = "Description is empty or only whitespace."
        else:
            is_incomplete, explanation = is_valid_acceptance_criteria_with_llm(description)
    
            if is_incomplete:
                issues.append("Acceptance Criteria Analysis")
                explanations["description"] = explanation

                # Generate Suggested AC only when description is flagged
                summary = story.get("summary", "")
                ac_suggestion = suggest_acceptance_criteria_with_llm(summary, description)
                # print ("Suggested Acceptance Criteria:", ac_suggestion)

    # --- Fix Version Check ---
    if "fixVersions" in present_fields:
        fixVersions = story.get("fixVersions", "")
        if isinstance(fixVersions, str) and not fixVersions.strip():
            issues.append("Missing target version")

    # --- Component Check ---
    if "components" in present_fields:
        component = story.get("component", "")
        if isinstance(component, str) and not component.strip():
            issues.append("Missing Component")

    return issues, explanations, ac_suggestion    
