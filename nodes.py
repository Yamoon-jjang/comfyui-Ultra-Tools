import json


MAX_TEXT_ENTRIES = 32
STATE_VERSION = 2
STATE_MARKER = "__ultra_textbox_multi__"


def _normalize_entry_records(payload):
    """Return (entry_id, text) pairs from v2 state or legacy plain text."""
    if payload is None:
        return [(None, "")]

    raw = str(payload)
    try:
        decoded = json.loads(raw)
    except (TypeError, ValueError, json.JSONDecodeError):
        # Backward compatibility: the original Ultra Textbox stored plain text.
        return [(None, raw)]

    if not (
        isinstance(decoded, dict)
        and decoded.get(STATE_MARKER) == STATE_VERSION
        and isinstance(decoded.get("entries"), list)
    ):
        # A textbox may legitimately contain JSON. Only our explicit state marker
        # is interpreted as multi-row metadata; all other JSON remains literal text.
        return [(None, raw)]

    records = []
    for item in decoded["entries"][:MAX_TEXT_ENTRIES]:
        if isinstance(item, dict):
            value = item.get("text", "")
            entry_id = item.get("id")
            entry_id = entry_id if isinstance(entry_id, str) and entry_id else None
        else:
            value = item
            entry_id = None
        records.append((entry_id, "" if value is None else str(value)))

    return records or [(None, "")]


def _normalize_entries(payload):
    """Compatibility helper returning only text values."""
    return [value for _entry_id, value in _normalize_entry_records(payload)]


def _source_name(index):
    """Backend key used by the dedicated STRING input for a zero-based row."""
    return "source" if index == 0 else f"source_{index + 1}"


class UltraTextbox:
    @classmethod
    def INPUT_TYPES(cls):
        sources = {
            _source_name(i): ("STRING", {"forceInput": True})
            for i in range(MAX_TEXT_ENTRIES)
        }
        return {
            "required": {
                # Kept as "text" for compatibility with existing workflows/API calls.
                # The frontend stores the multi-row state as JSON here; legacy plain
                # text remains valid and is treated as Text 1.
                "text": ("STRING", {"multiline": True, "default": ""}),
            },
            "optional": sources,
            "hidden": {
                "unique_id": "UNIQUE_ID",
            },
        }

    # ComfyUI validates links against the backend schema, so the backend exposes a
    # bounded pool of STRING outputs. The frontend only renders the active count.
    # This avoids unsupported runtime mutation of RETURN_TYPES while keeping the UI
    # truly dynamic.
    RETURN_TYPES = ("STRING",) * MAX_TEXT_ENTRIES
    RETURN_NAMES = tuple(
        "string" if i == 0 else f"string_{i + 1}" for i in range(MAX_TEXT_ENTRIES)
    )
    FUNCTION = "run"
    CATEGORY = "Ultra Tools"
    OUTPUT_NODE = True

    def run(self, text="", source=None, unique_id=None, **kwargs):
        records = _normalize_entry_records(text)
        active_count = min(len(records), MAX_TEXT_ENTRIES)
        entry_ids = [entry_id for entry_id, _value in records[:active_count]]
        values = [value for _entry_id, value in records[:active_count]]

        # Each visible row has its own dedicated STRING input. Just like the
        # original Ultra Textbox, a connected source is authoritative for that
        # execution. The frontend mirrors the executed value into the editable
        # textarea so the user can inspect/copy/edit it without ComfyUI's greyed
        # converted-widget presentation.
        for i in range(active_count):
            incoming = source if i == 0 else kwargs.get(_source_name(i))
            if incoming is not None:
                values[i] = str(incoming)

        result = values + [""] * (MAX_TEXT_ENTRIES - active_count)

        # Return the stable entry IDs that belonged to this queued execution.
        # If the user reorders/deletes rows while a slow upstream node is still
        # running, the frontend can map each completed value back to the same
        # logical Text row instead of applying stale results by slot index.
        return {
            "ui": {"text": values, "entry_ids": entry_ids},
            "result": tuple(result),
        }


NODE_CLASS_MAPPINGS = {
    "UltraTextbox": UltraTextbox,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "UltraTextbox": "Ultra Tools Textbox",
}
