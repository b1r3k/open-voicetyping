# Makefile for VoiceTyping GNOME Shell Extension

UUID = voicetyping@cx-lab.com
EXTENSION_DIR = $(HOME)/.local/share/gnome-shell/extensions/$(UUID)
SCHEMA_DIR = $(EXTENSION_DIR)/schemas

# Default target
all: install

# Install the extension
install: compile-schema
	@echo "Installing extension..."
	@mkdir -p $(EXTENSION_DIR)
	@cp -r * $(EXTENSION_DIR)/
	@echo "Extension installed to $(EXTENSION_DIR)"

# Compile GSettings schema
compile-schema:
	@echo "Compiling GSettings schema..."
	@mkdir -p $(SCHEMA_DIR)
	@cp schemas/* $(SCHEMA_DIR)/
	@glib-compile-schemas $(SCHEMA_DIR)

# Uninstall the extension
uninstall:
	@echo "Uninstalling extension..."
	@rm -rf $(EXTENSION_DIR)
	@rm -f $(SCHEMA_DIR)/org.gnome.shell.extensions.voicetyping.gschema.xml
	@glib-compile-schemas $(SCHEMA_DIR)
	@echo "Extension uninstalled"

# Enable the extension
enable:
	@gnome-extensions enable $(UUID)

# Disable the extension
disable:
	@gnome-extensions disable $(UUID)

# Show extension status
status:
	@gnome-extensions list | grep $(UUID) || echo "Extension not found"

# Clean up
clean:
	@rm -rf $(EXTENSION_DIR)
	@rm -f $(SCHEMA_DIR)/org.gnome.shell.extensions.voicetyping.gschema.xml

.PHONY: all install compile-schema uninstall enable disable status clean
