# backlog_refinement_agent/cli.py

from typing import List

import pandas as pd

from .config import settings
from .jira_client import fetch_issues_from_jira, post_comment_to_jira
from .slack_client import post_summary_to_slack
from .refinement import evaluate_story


def _load_stories() -> pd.DataFrame:
    """
    Either fetch from Jira or from a local CSV, depending on USE_JIRA.
    Returns a pandas DataFrame with at least:
      - id
      - summary
      - description
      - reporter
      - account_id
      - present_fields
    """
    if settings.jira.use_jira:
        print("🔄 Fetching issues from Jira...")
        df = fetch_issues_from_jira()

        print(f"📌 Total issues fetched: {len(df)}")
        for _, row in df.iterrows():
            print(f"   - {row.get('id', 'N/A')} | {row.get('summary', '')}")

        return df

    # Local CSV mode
    print(f"📄 Loading issues from local CSV: {settings.jira.local_file}")
    df = pd.read_csv(settings.jira.local_file)

    # Generate present_fields if not present
    if "present_fields" not in df.columns:
        present_fields_col = []
        for _, row in df.iterrows():
            fields = [
                col
                for col in df.columns
                if str(row[col]) not in ("", "nan", "NaN", None)
            ]
            present_fields_col.append(fields)
        df["present_fields"] = present_fields_col

    return df


def main() -> None:
    df = _load_stories()
    df.fillna("", inplace=True)

    slack_summary_blocks: List[str] = []
    flagged_count = 0

    for _, story in df.iterrows():
        story_id = story.get("id") or story.get("key") or "<unknown>"
        present_fields = story.get("present_fields", [])

        issues, explanations, ac_suggestion = evaluate_story(story, present_fields)

        # --- Explicit Missing Component logic based on Jira data ---
        components_val = story.get("components", "")
        has_components = bool(str(components_val).strip())

        if not has_components:
            # Components truly missing → ensure it's flagged
            if "Missing Component" not in issues:
                issues.append("Missing Component")
                explanations.setdefault(
                    "Missing Component",
                    "No Jira component is set for this story. "
                    "Please assign an appropriate component for better traceability.",
                )
        else:
            # Components are present → make sure we don't incorrectly flag it
            if "Missing Component" in issues:
                issues = [i for i in issues if i != "Missing Component"]
                explanations.pop("Missing Component", None)

        # Skip if nothing was flagged and no AC suggestion was generated
        if not issues and not ac_suggestion:
            continue


        flagged_count += 1

        print(f"\n🚩 Flagged Count: {flagged_count}, Story: {story_id}")
        print("Issues:", issues)
        print("Explanations:", explanations)
        if ac_suggestion:
            print("Suggested AC:\n", ac_suggestion)

        reporter_name = story.get("reporter", "")
        account_id = story.get("account_id", "")

        # ====================================================
        # JIRA COMMENT: Same structure as desired Slack format
        # ====================================================
        comment_lines: List[str] = []

        # Overall header
        comment_lines.append("Backlog Refinement Summary")
        header_line = f"- {story_id}"
        if reporter_name:
            header_line += f" (reported by {reporter_name})"
        comment_lines.append(header_line)
        comment_lines.append("")  # blank line

        # Per-issue analysis
        for issue in issues:
            comment_lines.append(f"  - {issue}")

            issue_lower = issue.lower()
            exp = None

            # Map issue to explanation keys
            if issue_lower.startswith("summary"):
                exp = explanations.get("summary")
            elif issue_lower.startswith("acceptance"):
                exp = explanations.get("description")
            else:
                exp = explanations.get(issue_lower) or explanations.get(issue)

            # Render explanation (if present)
            if exp:
                if isinstance(exp, dict):
                    for k, v in exp.items():
                        comment_lines.append(f"      {k}: {v}")
                else:
                    for line in str(exp).splitlines():
                        comment_lines.append(f"      {line}")
            else:
                comment_lines.append("      (no explanation available)")

            # --- Add AC SUGGESTION ONLY under 'Acceptance Criteria Analysis' ---
            if issue_lower.startswith("acceptance") and ac_suggestion:
                comment_lines.append("      Suggested Acceptance Criteria:")
                for line in str(ac_suggestion).splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    # Skip headings like "Suggested Acceptance Criteria"
                    if line.lower().startswith("suggested acceptance criteria"):
                        continue
                    if line.startswith("-"):
                        comment_lines.append(f"         {line}")
                    else:
                        comment_lines.append(f"         - {line}")

            # Add blank line between issues
            comment_lines.append("")


            comment_lines.append("")  # blank line between issues

        # Post to Jira
        post_comment_to_jira(
            issue_key=story_id,
            comment_lines=comment_lines,
            reporter_name=reporter_name,
            account_id=account_id,
        )

        # ====================================================
        # SLACK SUMMARY: keep the previous structure you liked
        # ====================================================
        slack_lines: List[str] = []

        first_line = f"- {story_id}"
        if reporter_name:
            first_line += f" (reported by @{reporter_name})"
        slack_lines.append(first_line)

        for issue in issues:
            slack_lines.append(f"  - {issue}")

            issue_lower = issue.lower()
            exp = None

            # Map issue to explanation key
            if issue_lower.startswith("summary"):
                exp = explanations.get("summary")
            elif issue_lower.startswith("acceptance"):
                exp = explanations.get("description")
            else:
                exp = explanations.get(issue_lower) or explanations.get(issue)

            if exp:
                if isinstance(exp, dict):
                    for k, v in exp.items():
                        slack_lines.append(f"      {k}: {v}")
                else:
                    for line in str(exp).splitlines():
                        slack_lines.append(f"      {line}")

                # AC suggestion note ONLY under Acceptance Criteria Analysis
                if issue_lower.startswith("acceptance") and ac_suggestion:
                    slack_lines.append(
                        "      Acceptance criteria suggestion added in Jira ticket's comment."
                    )
            else:
                slack_lines.append("      (no explanation available)")

            # ▬▬▬ Add a blank line after each issue block ▬▬▬
            slack_lines.append("")


        slack_summary_blocks.append("\n".join(slack_lines))

    # --------------------------------------------------------
    # Final Slack summary message
    # --------------------------------------------------------
    if not slack_summary_blocks:
        post_summary_to_slack("✅ No issues flagged in the backlog refinement run.")
    else:
        slack_message = (
            "*Backlog Refinement Summary*\n"
            f"Flagged Stories: {flagged_count}\n\n"
            + "\n\n".join(slack_summary_blocks)
        )
        post_summary_to_slack(slack_message)

    print("\n✅ Backlog refinement run complete.")


if __name__ == "__main__":
    main()
