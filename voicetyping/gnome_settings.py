import gi
import os
from gi.repository import Gio

from .logging import root_logger

gi.require_version("Gio", "2.0")

logger = root_logger.getChild(__name__)


class GNOMESettingsReader:
    def __init__(self, schema_id: str):
        self._schema_id = schema_id
        self._schema, self._settings = self._get_schema_and_settings(schema_id)

    def _get_schema_and_settings(self, schema_id, schema_dir=None):
        if schema_dir:
            source = Gio.SettingsSchemaSource.new_from_directory(
                schema_dir, Gio.SettingsSchemaSource.get_default(), False
            )
        else:
            # Try to find the extension's schema directory automatically
            schema_dir = self._find_extension_schema_dir(schema_id)
            logger.info("Schema directory: %s", schema_dir)
            if schema_dir:
                source = Gio.SettingsSchemaSource.new_from_directory(
                    schema_dir, Gio.SettingsSchemaSource.get_default(), False
                )
            else:
                source = Gio.SettingsSchemaSource.get_default()

        schema = source.lookup(schema_id, True)
        if not schema:
            raise ValueError(f"Schema '{schema_id}' not found")

        # Create settings using the same schema source that contains our extension's schemas
        if schema_dir:
            # Use the custom schema source for settings creation
            settings = Gio.Settings.new_full(schema, None, "/org/gnome/shell/extensions/voicetyping/")
        else:
            # Use default settings
            settings = Gio.Settings.new(schema_id)

        return schema, settings

    def _find_extension_schema_dir(self, schema_id: str) -> str:
        """Find the extension's schema directory automatically."""
        # Common paths where GNOME extensions store their schemas
        possible_paths = [
            # User's local extensions
            os.path.expanduser("~/.local/share/gnome-shell/extensions"),
            # System-wide extensions
            "/usr/share/gnome-shell/extensions",
            "/usr/local/share/gnome-shell/extensions",
        ]

        for base_path in possible_paths:
            if not os.path.exists(base_path):
                continue

            # Look for directories that might contain our extension
            for item in os.listdir(base_path):
                item_path = os.path.join(base_path, item)
                if not os.path.isdir(item_path):
                    continue

                # Check if this directory contains our schema
                schemas_dir = os.path.join(item_path, "schemas")
                if os.path.exists(schemas_dir):
                    schema_file = os.path.join(schemas_dir, f"{schema_id}.gschema.xml")
                    if os.path.exists(schema_file):
                        return schemas_dir

        return None

    def get_key(self, key: str) -> str:
        schema_obj = self._schema.get_key(key)
        obj_type = schema_obj.get_value_type().dup_string()
        match obj_type:
            case "s":
                return self._settings.get_string(key)
            case "b":
                return self._settings.get_boolean(key)
            case "i":
                return self._settings.get_int(key)
            case "d":
                return self._settings.get_double(key)
            case _:
                raise ValueError(f"Unsupported type: {obj_type}")
