"""HTML index generation for Caliper visualizations."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any


def generate_html_index(
    output_dir: Path,
    title: str = "Caliper Reports Index",
    include_subdirs: bool = True,
) -> str:
    """
    Generate an HTML index file listing all HTML files in the output directory.

    Args:
        output_dir: Directory containing HTML files to index
        title: Title for the index page
        include_subdirs: Whether to include HTML files from subdirectories

    Returns:
        Path to the generated index file
    """
    output_dir = output_dir.resolve()

    # Find all HTML files
    html_files = _find_html_files(output_dir, include_subdirs)

    # Generate the index HTML content
    html_content = _generate_index_html(html_files, output_dir, title)

    # Write the index file
    index_file = output_dir / "caliper_index.html"
    index_file.write_text(html_content, encoding="utf-8")

    return str(index_file)


def _find_html_files(output_dir: Path, include_subdirs: bool) -> list[dict[str, Any]]:
    """Find all HTML files in the output directory."""
    html_files = []

    if include_subdirs:
        pattern = "**/*.html"
    else:
        pattern = "*.html"

    for html_file in output_dir.glob(pattern):
        # Skip the index file itself if it exists
        if html_file.name == "caliper_index.html":
            continue

        # Get relative path from output_dir
        relative_path = html_file.relative_to(output_dir)

        # Get file stats
        stat = html_file.stat()
        modified_time = datetime.fromtimestamp(stat.st_mtime)
        file_size = stat.st_size

        html_files.append(
            {
                "path": str(relative_path),
                "name": html_file.name,
                "directory": str(relative_path.parent) if relative_path.parent != Path(".") else "",
                "modified": modified_time,
                "size": file_size,
                "size_human": _format_file_size(file_size),
            }
        )

    # Sort by directory then by name
    html_files.sort(key=lambda x: (x["directory"], x["name"]))

    return html_files


def _format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    if size_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    size = float(size_bytes)

    while size >= 1024.0 and i < len(size_names) - 1:
        size /= 1024.0
        i += 1

    if i == 0:
        return f"{int(size)} {size_names[i]}"
    else:
        return f"{size:.1f} {size_names[i]}"


def _generate_index_html(html_files: list[dict[str, Any]], output_dir: Path, title: str) -> str:
    """Generate the HTML content for the index page."""

    # Group files by directory
    files_by_directory = {}
    for file_info in html_files:
        directory = file_info["directory"] or "."
        if directory not in files_by_directory:
            files_by_directory[directory] = []
        files_by_directory[directory].append(file_info)

    # Generate HTML
    html_parts = []

    # HTML header
    html_parts.append(f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f8f9fa;
        }}

        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 8px;
            margin-bottom: 30px;
            text-align: center;
        }}

        .header h1 {{
            margin: 0 0 10px 0;
            font-size: 2.5em;
            font-weight: 300;
        }}

        .header .meta {{
            opacity: 0.9;
            font-size: 1.1em;
        }}

        .summary {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}

        .summary h2 {{
            margin: 0 0 15px 0;
            color: #495057;
            font-size: 1.3em;
        }}

        .stats {{
            display: flex;
            gap: 30px;
            flex-wrap: wrap;
        }}

        .stat {{
            text-align: center;
        }}

        .stat .number {{
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
            display: block;
        }}

        .stat .label {{
            color: #6c757d;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .directory-section {{
            background: white;
            margin-bottom: 20px;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}

        .directory-header {{
            background: #f1f3f4;
            padding: 15px 20px;
            border-bottom: 1px solid #e9ecef;
        }}

        .directory-header h3 {{
            margin: 0;
            color: #495057;
            font-size: 1.1em;
            display: flex;
            align-items: center;
        }}

        .directory-header .folder-icon {{
            margin-right: 8px;
            font-size: 1.2em;
        }}

        .file-list {{
            padding: 0;
        }}

        .file-item {{
            display: flex;
            align-items: center;
            padding: 15px 20px;
            border-bottom: 1px solid #f8f9fa;
            transition: background-color 0.2s;
        }}

        .file-item:hover {{
            background-color: #f8f9fa;
        }}

        .file-item:last-child {{
            border-bottom: none;
        }}

        .file-icon {{
            margin-right: 12px;
            font-size: 1.1em;
            color: #dc3545;
        }}

        .file-info {{
            flex: 1;
        }}

        .file-name {{
            font-weight: 500;
            color: #007bff;
            text-decoration: none;
            font-size: 1.05em;
        }}

        .file-name:hover {{
            text-decoration: underline;
        }}

        .file-meta {{
            font-size: 0.85em;
            color: #6c757d;
            margin-top: 3px;
        }}

        .no-files {{
            text-align: center;
            padding: 40px;
            color: #6c757d;
            font-style: italic;
        }}

        .footer {{
            text-align: center;
            margin-top: 40px;
            padding: 20px;
            color: #6c757d;
            font-size: 0.9em;
        }}

        @media (max-width: 768px) {{
            body {{
                padding: 10px;
            }}

            .header h1 {{
                font-size: 2em;
            }}

            .stats {{
                justify-content: center;
            }}

            .file-item {{
                padding: 12px 15px;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 {title}</h1>
        <div class="meta">
            Generated on {datetime.now().strftime("%Y-%m-%d at %H:%M:%S")}
        </div>
        <div class="meta">
            📁 {output_dir}
        </div>
    </div>""")

    # Summary statistics
    total_files = len(html_files)
    total_directories = len(files_by_directory)
    total_size = sum(f["size"] for f in html_files)

    html_parts.append(f"""
    <div class="summary">
        <h2>📈 Summary</h2>
        <div class="stats">
            <div class="stat">
                <span class="number">{total_files}</span>
                <span class="label">HTML Files</span>
            </div>
            <div class="stat">
                <span class="number">{total_directories}</span>
                <span class="label">Directories</span>
            </div>
            <div class="stat">
                <span class="number">{_format_file_size(total_size)}</span>
                <span class="label">Total Size</span>
            </div>
        </div>
    </div>""")

    # File listings by directory
    if not html_files:
        html_parts.append("""
    <div class="directory-section">
        <div class="no-files">
            No HTML files found in the output directory.
        </div>
    </div>""")
    else:
        for directory in sorted(files_by_directory.keys()):
            files = files_by_directory[directory]

            # Directory header
            display_dir = "📁 Root Directory" if directory == "." else f"📁 {directory}"
            html_parts.append(f"""
    <div class="directory-section">
        <div class="directory-header">
            <h3><span class="folder-icon">📂</span>{display_dir}</h3>
        </div>
        <div class="file-list">""")

            # File list
            for file_info in files:
                modified_str = file_info["modified"].strftime("%Y-%m-%d %H:%M")
                html_parts.append(f"""
            <div class="file-item">
                <div class="file-icon">📄</div>
                <div class="file-info">
                    <a href="{file_info["path"]}" class="file-name" target="_blank">{file_info["name"]}</a>
                    <div class="file-meta">
                        {file_info["size_human"]} • Modified {modified_str}
                    </div>
                </div>
            </div>""")

            html_parts.append("""
        </div>
    </div>""")

    # Footer
    html_parts.append("""
    <div class="footer">
        Generated by Caliper HTML Index Generator<br>
        <small>This index automatically lists all HTML files in the output directory.</small>
    </div>
</body>
</html>""")

    return "".join(html_parts)
