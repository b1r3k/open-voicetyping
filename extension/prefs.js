/* preferences.js
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * SPDX-License-Identifier: GPL-2.0-or-later
 */

import GObject from 'gi://GObject';
import Gtk from 'gi://Gtk';
import Adw from 'gi://Adw';
import GLib from 'gi://GLib';

import {ExtensionPreferences, gettext as _} from 'resource:///org/gnome/Shell/Extensions/js/extensions/prefs.js';

export default class VoiceTypingPreferences extends ExtensionPreferences {
    fillPreferencesWindow(window) {
        // Use the same GSettings schema as in extension.js
        const page = new Adw.PreferencesPage();

        // Add description group
        const descriptionGroup = new Adw.PreferencesGroup({
            title: _('Configuration'),
            description: _('Configure your OpenAI API credentials to enable voice typing functionality.'),
        });
        page.add(descriptionGroup);

        const group = new Adw.PreferencesGroup();
        page.add(group);

        // API Key setting
        const apiKeyRow = new Adw.EntryRow({
            title: _('OpenAI API Key'),
        });
        group.add(apiKeyRow);

        // API URL setting
        const apiUrlRow = new Adw.EntryRow({
            title: _('OpenAI API URL'),
        });
        group.add(apiUrlRow);

        // Add Save button
        const saveButton = new Gtk.Button({
            label: _('Save Settings'),
            css_classes: ['suggested-action'],
        });
        group.add(saveButton);

        // Bind settings
        window._settings = this.getSettings();

        // Bind API Key setting
        window._settings.bind('openai-api-key', apiKeyRow, 'text',
            GObject.BindingFlags.BIDIRECTIONAL
        );

        // Bind API URL setting
        window._settings.bind('openai-api-url', apiUrlRow, 'text',
            GObject.BindingFlags.BIDIRECTIONAL
        );

        // Save button handler
        saveButton.connect('clicked', () => {
            const apiKey = apiKeyRow.get_text();
            const apiUrl = apiUrlRow.get_text();

            window._settings.set_string('openai-api-key', apiKey);
            window._settings.set_string('openai-api-url', apiUrl);

            console.debug('Settings saved - API Key:', apiKey, 'API URL:', apiUrl);

        });

        window.add(page);
    }
}
