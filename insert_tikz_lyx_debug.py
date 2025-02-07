#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
insert_tikz_lyx_debug.py

Inserts a new layout block:

  \begin_layout Plain Layout
  \backslash
  tikzsetnextfilename{<prefix><N>}
  \end_layout

BEFORE each layout block that has:
    \backslash
    begin{tikzpicture} or
    \backslash
    begin{quantikz}
(if no existing tikzsetnextfilename is found in the same or preceding layout block).

Operates only inside ERT blocks (\begin_inset ERT ... \end_inset).
We split each ERT block into separate "layout blocks" (\begin_layout Plain Layout ... \end_layout).

Usage:
  ./insert_tikz_lyx_debug.py mydoc.lyx --start-index 1 --prefix qcpict
"""

import re
import argparse
import sys
from typing import List, Tuple

##############################################################################
# Regex Patterns
##############################################################################

ENV_LINE_RE = re.compile(
    # Matches a line that has \backslash\n begin{tikzpicture} or \backslash\n begin{quantikz}.
    # Possibly with bracket [stuff], on the same line.
    # We'll do a simple search in each layout block text.
    r'\\backslash\s*\n?\s*begin\{(tikzpicture|quantikz)\}'
)

# MODIFIED: allow multiple newlines/spaces after \backslash
# and before 'tikzsetnextfilename'. Also use DOTALL for safety.
TIKZSET_RE = re.compile(
    r'\\backslash\s*(?:\n\s*)*tikzsetnextfilename\{([^}]+)\}',
    re.DOTALL
)

##############################################################################
# Arg parsing
##############################################################################

def parse_arguments():
    parser = argparse.ArgumentParser(description="Insert layout blocks with "
                                     "tikzsetnextfilename commands inside ERT blocks.")
    parser.add_argument("file", help="Path to the .lyx file.")
    parser.add_argument("--start-index", "-s", type=int, default=1,
                        help="Start numbering from this integer (default=1).")
    parser.add_argument("--prefix", "-p", default="qcpict",
                        help="Filename prefix (default='qcpict').")
    return parser.parse_args()


##############################################################################
# Step 1) Identify ERT blocks in the file
##############################################################################

def find_ert_blocks(lines: List[str]) -> List[Tuple[int,int]]:
    """
    Find all ERT blocks delimited by:
      \begin_inset ERT
      ...
      \end_inset
    Returns list of (start_idx, end_idx) inclusive.
    """
    ert_blocks = []
    inside = False
    start_i = -1
    for i, line in enumerate(lines):
        if not inside and "\\begin_inset ERT" in line:
            inside = True
            start_i = i
        elif inside and "\\end_inset" in line:
            ert_blocks.append((start_i, i))
            inside = False
    return ert_blocks


##############################################################################
# Step 2) Inside each ERT, we split text into layout blocks
##############################################################################

def split_into_layout_blocks(ert_block_lines: List[str]) -> List[List[str]]:
    """
    Within an ERT block, we typically see something like:
      \begin_layout Plain Layout
        ...
      \end_layout
      \begin_layout Plain Layout
        ...
      \end_layout
    We'll split these into separate lists of lines.

    If there's text outside \begin_layout ... \end_layout pairs, 
    that becomes its own block as well.
    """
    blocks: List[List[str]] = []
    current: List[str] = []
    in_layout = False

    for line in ert_block_lines:
        if "\\begin_layout Plain Layout" in line:
            # Start of a new layout block
            if current:
                blocks.append(current)
            current = [line]
            in_layout = True
        elif "\\end_layout" in line and in_layout:
            current.append(line)
            blocks.append(current)
            current = []
            in_layout = False
        else:
            current.append(line)

    # any remainder
    if current:
        blocks.append(current)

    return blocks


def join_layout_blocks(blocks: List[List[str]]) -> List[str]:
    """
    Flatten the list-of-lists back into lines.
    """
    out: List[str] = []
    for b in blocks:
        out.extend(b)
    return out


##############################################################################
# Step 3) Searching each layout block for environment or tikzset lines
##############################################################################

def has_environment(lines_block: List[str]) -> bool:
    """Return True if the block contains a line that matches ENV_LINE_RE."""
    text = "\n".join(lines_block)
    return bool(ENV_LINE_RE.search(text))


def has_tikzset(lines_block: List[str]) -> bool:
    """Return True if lines_block has any 'tikzsetnextfilename{...}' 
       (with possible multiline after \backslash)."""
    text = "\n".join(lines_block)
    match = TIKZSET_RE.search(text)
    if not match:
        # Extra debug: show the block if we suspect there's a command we didn't catch
        # Uncomment if you want REALLY verbose block printing:
        #
        # print("      [DEBUG] has_tikzset? No match in block lines:")
        # for ln in lines_block:
        #     print(f"         {ln.rstrip()}")
        pass
    return bool(match)


def get_tikz_indices(lines_block: List[str], prefix: str) -> List[int]:
    """
    Return all integer indices in lines_block that match:
      \backslash
      tikzsetnextfilename{<prefix><N>}
    (with possible extra whitespace/newlines).
    """
    text = "\n".join(lines_block)
    # We just replace the prefix in the pattern:
    pat = re.compile(
        rf'\\backslash\s*(?:\n\s*)*tikzsetnextfilename\{{{prefix}(\d+)\}}',
        re.DOTALL
    )
    return [int(m.group(1)) for m in pat.finditer(text)]


##############################################################################
# Step 4) Insert a new layout block with tikzset if needed
##############################################################################

def make_tikz_layout(prefix: str, idx: int) -> List[str]:
    """
    Return lines for:
      \begin_layout Plain Layout
      \backslash
      tikzsetnextfilename{prefixN}
      \end_layout
    """
    return [
        r"\begin_layout Plain Layout" + "\n",
        r"\backslash" + "\n",
        f"tikzsetnextfilename{{{prefix}{idx}}}\n",
        r"\end_layout" + "\n"
    ]


def insert_tikz_in_ert(ert_lines: List[str], prefix: str, start_idx: int) -> Tuple[List[str], int]:
    """
    Split ERT into layout blocks, then for each block that has an environment,
    check if it or the block above has 'tikzsetnextfilename'.
    If not, insert a new layout block above it.

    Return (new ERT lines, updated next_index).
    """
    blocks = split_into_layout_blocks(ert_lines)
    i = 0
    current_index = start_idx

    print(f"  [DEBUG] ERT block has {len(blocks)} layout blocks.")
    while i < len(blocks):
        block = blocks[i]
        # debug
        text_head = (block[0].strip() if block else "")
        print(f"    [DEBUG] LayoutBlock #{i}: first line='{text_head}'")

        if has_environment(block):
            print(f"    [DEBUG] -> Found environment in layout block #{i}.")
            # check if this block or previous block has tikzset
            if has_tikzset(block):
                print(f"    [DEBUG] -> Already has tikzset in same block. Skipping insertion.")
            else:
                if i > 0 and has_tikzset(blocks[i - 1]):
                    print(f"    [DEBUG] -> Found tikzset in previous block. Skipping insertion.")
                else:
                    print(f"    [DEBUG] -> Inserting new layout block with tikzset for index {current_index}")
                    new_block = make_tikz_layout(prefix, current_index)
                    blocks.insert(i, new_block)
                    current_index += 1
                    i += 1
        i += 1

    return (join_layout_blocks(blocks), current_index)


##############################################################################
# Step 5) Main flow
##############################################################################

def main():
    args = parse_arguments()

    # read lines
    try:
        with open(args.file, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"Error: file not found: {args.file}")
        sys.exit(1)

    # find ERT blocks
    ert_blocks = find_ert_blocks(lines)
    if not ert_blocks:
        print("No ERT blocks found. Nothing to do.")
        sys.exit(0)

    print(f"Found {len(ert_blocks)} ERT blocks.")

    # find existing max index
    max_found = 0
    for (start_i, end_i) in ert_blocks:
        block_lines = lines[start_i:end_i+1]
        # parse layout blocks
        lb = split_into_layout_blocks(block_lines)
        for subblock in lb:
            used_nums = get_tikz_indices(subblock, args.prefix)
            if used_nums:
                max_found = max(max_found, max(used_nums))

    start_val = max(args.start_index, max_found + 1)
    print(f"Existing maximum found: {max_found}")
    print(f"Starting new numbering from: {start_val}")
    proceed = input("Proceed? [y/n]: ").strip().lower()
    if proceed not in ("y", "yes"):
        print("Aborted.")
        sys.exit(0)

    new_lines: List[str] = []
    prev_end = -1
    next_index = start_val

    # process each ERT
    for i, (start_i, end_i) in enumerate(ert_blocks):
        print(f"[DEBUG] Processing ERT block #{i} (lines {start_i}-{end_i})")

        # copy everything prior to this block
        new_lines.extend(lines[prev_end+1:start_i])
        ert_content = lines[start_i:end_i+1]

        # do insertion
        modified_ert, updated_idx = insert_tikz_in_ert(ert_content, args.prefix, next_index)
        next_index = updated_idx

        new_lines.extend(modified_ert)
        prev_end = end_i

    # copy tail
    if ert_blocks:
        last_end = ert_blocks[-1][1]
        new_lines.extend(lines[last_end+1:])

    # write
    with open(args.file, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    print(f"]Done. Final index used: {next_index - 1}.")


if __name__ == "__main__":
    main()
