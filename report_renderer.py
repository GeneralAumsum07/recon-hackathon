# report_renderer.py
import datetime
import os
import json

def render_markdown_report(fragment, gemini_json, search_results, out_dir="recon_reports"):
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"recon_{ts}.md"
    path = os.path.join(out_dir, filename)

    md_lines = []
    md_lines.append(f"# Reconstruction Report — {ts}\n")
    md_lines.append("## Original Fragment\n")
    md_lines.append(f"> {fragment}\n")
    md_lines.append("## AI-Reconstructed Text\n")
    md_lines.append(f"> {gemini_json.get('reconstructed_text')}\n")
    md_lines.append("\n### Explanations\n")
    for e in gemini_json.get("explanations", []):
        md_lines.append(f"- {e}")
    md_lines.append(f"\n**Confidence**: {gemini_json.get('confidence')}\n")
    md_lines.append("\n## Contextual Sources\n")
    for i, r in enumerate(search_results, start=1):
        md_lines.append(f"{i}. [{r['title']}]({r['url']}) — {r.get('snippet','')}")
    md_lines.append("\n---\n")
    md_lines.append("### Raw JSON (for graders)\n")
    md_lines.append("```json\n")
    md_lines.append(json.dumps({
        "fragment": fragment,
        "gemini": gemini_json,
        "sources": search_results
    }, indent=2))
    md_lines.append("\n```\n")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    return path
