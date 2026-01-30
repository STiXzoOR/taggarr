"""NFO file parsing and updates for Kodi/Emby."""

import os
import logging
import xml.etree.ElementTree as ET

logger = logging.getLogger("taggarr")

MANAGED_TAGS = {"dub", "semi-dub", "wrong-dub"}


def safe_parse(path):
    """Parse NFO file, handling common corruption issues."""
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    if "</tvshow>" in content:
        content = content.split("</tvshow>")[0] + "</tvshow>"
    return ET.fromstring(content)


def get_genres(nfo_path):
    """Extract genre list from NFO file."""
    try:
        root = safe_parse(nfo_path)
        return [g.text.lower() for g in root.findall("genre") if g.text]
    except Exception as e:
        logger.warning(f"Genre parsing failed for {nfo_path}: {e}")
        return []


def update_tag(nfo_path, tag_value, dry_run=False):
    """Update <tag> element in TV show NFO file."""
    _update_tag_impl(nfo_path, tag_value, dry_run)


def update_movie_tag(nfo_path, tag_value, dry_run=False):
    """Update <tag> element in movie NFO file."""
    _update_tag_impl(nfo_path, tag_value, dry_run, is_movie=True)


def _update_tag_impl(nfo_path, tag_value, dry_run, is_movie=False):
    """Shared implementation for tag updates."""
    try:
        tree = ET.parse(nfo_path)
        root = tree.getroot()

        # Remove existing managed tags
        for t in root.findall("tag"):
            if t.text and t.text.strip().lower() in MANAGED_TAGS:
                root.remove(t)

        # Insert new tag at first position
        new_tag = ET.Element("tag")
        new_tag.text = tag_value

        insert_index = 0
        for i, elem in enumerate(root):
            if elem.tag == "tag":
                insert_index = i
                break
        root.insert(insert_index, new_tag)

        if dry_run:
            logger.info(f"[Dry Run] Would update <tag>{tag_value}</tag> in {os.path.basename(nfo_path)}")
        else:
            ET.indent(tree, space="  ")
            tree.write(nfo_path, encoding="utf-8", xml_declaration=False)
            label = "movie NFO" if is_movie else "NFO"
            logger.info(f"Updated <tag>{tag_value}</tag> in {label}: {os.path.basename(nfo_path)}")
    except Exception as e:
        logger.warning(f"Failed to update <tag> in NFO: {e}")


def update_genre(nfo_path, should_have_dub, dry_run=False):
    """Add or remove <genre>Dub</genre> based on tag status."""
    try:
        tree = ET.parse(nfo_path)
        root = tree.getroot()
        genres = [g.text.strip().lower() for g in root.findall("genre") if g.text]
        has_dub = "dub" in genres

        if should_have_dub == has_dub:
            return  # No change needed

        modified = False

        if should_have_dub and not has_dub:
            new_genre = ET.Element("genre")
            new_genre.text = "Dub"
            first_genre = root.find("genre")
            if first_genre is not None:
                idx = list(root).index(first_genre)
            else:
                idx = len(root)
            root.insert(idx, new_genre)
            modified = True
            logger.info(f"Adding <genre>Dub</genre> to {os.path.basename(nfo_path)}")

        elif not should_have_dub and has_dub:
            for g in root.findall("genre"):
                if g.text and g.text.strip().lower() == "dub":
                    root.remove(g)
                    modified = True
            logger.info(f"Removing <genre>Dub</genre> from {os.path.basename(nfo_path)}")

        if modified and not dry_run:
            ET.indent(tree, space="  ")
            tree.write(nfo_path, encoding="utf-8", xml_declaration=False)
        elif modified and dry_run:
            logger.info(f"[Dry Run] Would update NFO file: {os.path.basename(nfo_path)}")

    except Exception as e:
        logger.warning(f"Failed to update NFO genre: {e}")
