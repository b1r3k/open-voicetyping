# VoiceTyping GNOME Shell Extension

A GNOME Shell extension that allows you to convert voice to keyboard input using OpenAI's speech-to-text API.

## Features

- Voice-to-text conversion using OpenAI API
- Configurable API settings through preferences dialog
- System tray indicator for easy access
- Secure storage of API credentials

## Installation

### Prerequisites

- GNOME Shell 47 or later
- OpenAI API key

### Installation Steps

1. Clone or download this extension
2. Navigate to the extension directory
3. Run the installation:
   ```bash
   cd extension
   make install
   ```
4. Enable the extension:
   ```bash
   make enable
   ```
5. Restart GNOME Shell (Alt+F2, type 'r', press Enter)

## Configuration

1. Open GNOME Extensions app
2. Find "VoiceTyping" in the list
3. Click the settings gear icon
4. Enter your OpenAI API key and URL
5. Click "Test Connection" to verify your settings

### Settings

- **OpenAI API Key**: Your OpenAI API key for authentication
- **OpenAI API URL**: The API endpoint URL (default: https://api.openai.com/v1)

## Usage

1. Click the microphone icon in the system tray
2. Select "Start Voice Typing" from the menu
3. Speak into your microphone
4. The transcribed text will be inserted as keyboard input

## Development

### Building from Source

```bash
cd extension
make install
make enable
```

### Uninstalling

```bash
make disable
make uninstall
```

### Available Make Targets

- `make install` - Install the extension
- `make enable` - Enable the extension
- `make disable` - Disable the extension
- `make uninstall` - Uninstall the extension
- `make status` - Show extension status
- `make clean` - Clean up installation files

## Troubleshooting

1. **Extension not appearing**: Restart GNOME Shell
2. **Settings not saving**: Check if the GSettings schema is properly compiled
3. **API errors**: Verify your OpenAI API key and URL in the preferences

## License

This extension is licensed under the GNU General Public License v2.0 or later.

## Contributing

Feel free to submit issues and pull requests to improve this extension.
