#!/usr/bin/env python3
# PR‑tracker: generates a combo chart from the collected PR data.
# deps: pandas, matplotlib, numpy

from pathlib import Path
import pandas as pd
import matplotlib

matplotlib.use("Agg")  # headless
import matplotlib.pyplot as plt
import numpy as np
import datetime as dt
import re


def generate_chart(csv_file=None):
    # Default to data.csv if no file specified
    if csv_file is None:
        csv_file = Path("data.csv")

    # Ensure file exists
    if not csv_file.exists():
        print(f"Error: {csv_file} not found.")
        print("Run collect_data.py first to collect data.")
        return False

    # Create chart
    df = pd.read_csv(csv_file)
    # Fix timestamp format - replace special dash characters with regular hyphens
    df["timestamp"] = df["timestamp"].str.replace("‑", "-")
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # Check if data exists
    if len(df) == 0:
        print("Error: No data found in CSV file.")
        return False
        
    # Limit to 8 data points spread across the entire dataset to avoid chart getting too busy
    total_points = len(df)
    if total_points > 8:
        # Create evenly spaced indices across the entire dataset
        indices = np.linspace(0, total_points - 1, num=8, dtype=int)
        df = df.iloc[indices]
        print(f"Limited chart to 8 data points evenly distributed across {total_points} total points.")

    # Adjust chart size based on data points
    num_points = len(df)
    if num_points <= 3:
        fig_width = max(10, num_points * 4)
        fig_height = 6
    else:
        fig_width = 14
        fig_height = 8

    # Create the combination chart
    fig, ax1 = plt.subplots(figsize=(fig_width, fig_height))

    # Prepare data
    x = np.arange(len(df))
    # Adjust bar width based on number of data points
    # We now have 4 groups of bars: Copilot (total/merged), Codex (total/merged), Devin (commits), Jules (commits)
    # So we need to accommodate them. Let's assign positions:
    # New bar positions:
    # Copilot Total: x - 1.5 * width (originally x - width/2 based on example, but keeping groups for now)
    # Codex Total:   x - 0.5 * width (originally x + width/2 based on example)
    # Devin Commits: x + 0.5 * width
    # Jules Commits: x + 1.5 * width
    # Let's try the example positions: Copilot @ x - width/2, Codex @ x + width/2
    # This means the effective group centers are:
    # Copilot: -0.5 * width
    # Codex:    0.5 * width
    # Devin:    1.5 * width (shifting by +width)
    # Jules:    2.5 * width (shifting by +width)
    width = min(0.20, 0.8 / max(1, num_points * 0.8)) # Adjusted width for more bars

    # Bar charts for totals
    bars_copilot_total = ax1.bar(
        x - width / 2, # Centered example
        df["copilot_total"],
        width,
        label="Copilot Total",
        alpha=0.7,
        color="#87CEEB",
    )

    bars_codex_total = ax1.bar(
        x + width / 2, # Centered example
        df["codex_total"],
        width,
        label="Codex Total",
        alpha=0.7,
        color="#FFA07A",
    )

    bars_devin_commits = ax1.bar(
        x + 1.5 * width, # Shifted right to make space
        df["devin_commits"],
        width,
        label="Devin Commits",
        alpha=0.7,
        color="#90EE90", # Light Green
    )

    bars_jules_commits = ax1.bar(
        x + 2.5 * width, # Shifted right further to make space
        df["jules_commits"],
        width,
        label="Jules Commits",
        alpha=0.7,
        color="#DDA0DD", # Plum
    )

    # Customize the chart
    ax1.set_xlabel("Data Points", fontsize=12, fontweight="bold")
    ax1.set_ylabel(
        "Counts (PRs & Commits)", fontsize=12, fontweight="bold", color="black"
    )

    title = "PR Analytics: Volume Comparison"
    ax1.set_title(title, fontsize=16, fontweight="bold", pad=20)

    # Set x-axis labels with timestamps
    timestamps = df["timestamp"].dt.strftime("%m-%d %H:%M")
    ax1.set_xticks(x)
    ax1.set_xticklabels(timestamps, rotation=45)

    # Add legend
    ax1.legend(loc="upper left", bbox_to_anchor=(0, 0.95))

    # Add grid
    ax1.grid(True, alpha=0.3, linestyle="--")

    # Add value labels on bars (with safety checks)
    def add_value_labels(ax, bars, format_str="{:.0f}"):
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                # Ensure the label fits within reasonable bounds
                label_text = format_str.format(height)
                if len(label_text) > 10:  # Truncate very long numbers
                    if height >= 1000:
                        label_text = f"{height/1000:.1f}k"
                    elif height >= 1000000:
                        label_text = f"{height/1000000:.1f}M"

                ax.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    height,
                    label_text,
                    ha="center",
                    va="bottom",
                    fontsize=9,
                    fontweight="bold",
                )

    add_value_labels(ax1, bars_copilot_total)
    add_value_labels(ax1, bars_codex_total)
    add_value_labels(ax1, bars_devin_commits)
    add_value_labels(ax1, bars_jules_commits)

    plt.tight_layout()

    # Save chart with appropriate DPI for CI environments
    chart_file = Path("chart.png")
    dpi = 150 if num_points <= 5 else 300
    fig.savefig(chart_file, dpi=dpi, bbox_inches="tight", facecolor="white")
    print(f"Chart generated: {chart_file}")
    
    # Also save chart to docs directory for GitHub Pages
    docs_dir = Path("docs")
    if docs_dir.exists():
        docs_chart_file = docs_dir / "chart.png"
        fig.savefig(docs_chart_file, dpi=dpi, bbox_inches="tight", facecolor="white")
        print(f"Chart copied to GitHub Pages: {docs_chart_file}")

    # Update the README with latest statistics
    update_readme(df)
    
    # Update the GitHub Pages with latest statistics
    update_github_pages(df)

    return True


def update_readme(df):
    """Update the README.md with the latest statistics"""
    readme_path = Path("README.md")

    # Skip if README doesn't exist
    if not readme_path.exists():
        print(f"Warning: {readme_path} not found, skipping README update.")
        return False

    # Get the latest data
    latest = df.iloc[-1]

    # Format numbers with commas
    copilot_total = f"{latest.copilot_total:,}"
    # copilot_merged = f"{latest.copilot_merged:,}" # Removed
    codex_total = f"{latest.codex_total:,}"
    # codex_merged = f"{latest.codex_merged:,}" # Removed
    devin_commits = f"{latest.devin_commits:,}"
    jules_commits = f"{latest.jules_commits:,}"
    # copilot_rate = (latest.copilot_merged / latest.copilot_total * 100) if latest.copilot_total > 0 else 0 # Removed
    # codex_rate = (latest.codex_merged / latest.codex_total * 100) if latest.codex_total > 0 else 0 # Removed

    # Create the new table content
    table_content = f"""## Current Statistics

| Service | Total PRs | Total Commits |
| ------- | --------- | ------------- |
| Copilot | {copilot_total} | N/A           |
| Codex   | {codex_total} | N/A           |
| Devin   | N/A       | {devin_commits} |
| Jules   | N/A       | {jules_commits} |"""

    # Read the current README content
    readme_content = readme_path.read_text()

    # Split content at the statistics header (if it exists)
    if "## Current Statistics" in readme_content:
        base_content = readme_content.split("## Current Statistics")[0].rstrip()
        new_content = f"{base_content}\n\n{table_content}"
    else:
        new_content = f"{readme_content}\n\n{table_content}"

    # Write the updated content back
    readme_path.write_text(new_content)
    print(f"README.md updated with latest statistics.")
    return True


def update_github_pages(df):
    """Update the GitHub Pages website with the latest statistics"""
    index_path = Path("docs/index.html")
    
    # Skip if index.html doesn't exist
    if not index_path.exists():
        print(f"Warning: {index_path} not found, skipping GitHub Pages update.")
        return False
    
    # Get the latest data
    latest = df.iloc[-1]
    
    # Format numbers with commas
    copilot_total = f"{latest.copilot_total:,}"
    # copilot_merged = f"{latest.copilot_merged:,}" # Removed
    codex_total = f"{latest.codex_total:,}"
    # codex_merged = f"{latest.codex_merged:,}" # Removed
    devin_commits = f"{latest.devin_commits:,}"
    jules_commits = f"{latest.jules_commits:,}"
    # copilot_rate = (latest.copilot_merged / latest.copilot_total * 100) if latest.copilot_total > 0 else 0 # Removed
    # codex_rate = (latest.codex_merged / latest.codex_total * 100) if latest.codex_total > 0 else 0 # Removed
    
    # Current timestamp for last updated
    timestamp = dt.datetime.now().strftime("%B %d, %Y %H:%M UTC")
    
    # Read the current index.html content
    index_content = index_path.read_text()

    # Define new table structure (header and rows)
    new_header_row = '<tr>\n                        <th>Service</th>\n                        <th>Total PRs</th>\n                        <th>Total Commits</th>\n                    </tr>'
    
    copilot_row_html = f'<tr>\n                        <td>Copilot</td>\n                        <td>{copilot_total}</td>\n                        <td>N/A</td>\n                    </tr>'
    codex_row_html = f'<tr>\n                        <td>Codex</td>\n                        <td>{codex_total}</td>\n                        <td>N/A</td>\n                    </tr>'
    devin_row_html = f'<tr>\n                        <td>Devin</td>\n                        <td>N/A</td>\n                        <td>{devin_commits}</td>\n                    </tr>'
    jules_row_html = f'<tr>\n                        <td>Jules</td>\n                        <td>N/A</td>\n                        <td>{jules_commits}</td>\n                    </tr>'

    # Update table header
    index_content = re.sub(
        r'<thead>\s*<tr>.*?</tr>\s*</thead>',
        f'<thead>\n                    {new_header_row}\n                </thead>',
        index_content,
        flags=re.DOTALL
    )

    # Update or add Copilot row
    copilot_row_pattern = re.compile(r'<tr>\s*<td>Copilot</td>.*?</tr>', re.DOTALL)
    if copilot_row_pattern.search(index_content):
        index_content = copilot_row_pattern.sub(copilot_row_html, index_content)
    else:
        # Add if not found (should always be found if tbody exists)
        index_content = index_content.replace('</tbody>', f'{copilot_row_html}\n                    </tbody>')

    # Update or add Codex row
    codex_row_pattern = re.compile(r'<tr>\s*<td>Codex</td>.*?</tr>', re.DOTALL)
    if codex_row_pattern.search(index_content):
        index_content = codex_row_pattern.sub(codex_row_html, index_content)
    else:
        index_content = index_content.replace('</tbody>', f'{codex_row_html}\n                    </tbody>')

    # Update or add Devin row
    devin_row_pattern = re.compile(r'<tr>\s*<td>Devin</td>.*?</tr>', re.DOTALL)
    if devin_row_pattern.search(index_content):
        index_content = devin_row_pattern.sub(devin_row_html, index_content)
    else:
        index_content = index_content.replace('</tbody>', f'{devin_row_html}\n                    </tbody>')

    # Add or update Jules row
    jules_row_pattern = re.compile(r'<tr>\s*<td>Jules</td>.*?</tr>', re.DOTALL)
    if jules_row_pattern.search(index_content):
        index_content = jules_row_pattern.sub(jules_row_html, index_content)
    else:
        # Insert before the last </tbody>
        parts = index_content.rsplit('</tbody>', 1)
        if len(parts) == 2:
            index_content = parts[0] + f'{jules_row_html}\n                    </tbody>' + parts[1]
        else: # Fallback if rsplit doesn't find tbody (e.g. empty tbody)
            index_content = index_content.replace('</tbody>', f'{jules_row_html}\n                    </tbody>')

    # Update the last updated timestamp
    index_content = re.sub(
        r'<span id="last-updated">[^<]*</span>',
        f'<span id="last-updated">{timestamp}</span>',
        index_content
    )
    
    # Write the updated content back
    index_path.write_text(index_content)
    print(f"GitHub Pages updated with latest statistics.")
    return True


if __name__ == "__main__":
    generate_chart()
