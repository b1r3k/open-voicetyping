/* extension.js
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
import St from 'gi://St';

import {Extension, gettext as _} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';

import * as Main from 'resource:///org/gnome/shell/ui/main.js';

const Indicator = GObject.registerClass(
class Indicator extends PanelMenu.Button {
    _init(settings) {
        super._init(0.0, _('Voice Typing'));

        this.settings = settings;

        this.add_child(new St.Icon({
            icon_name: 'audio-input-microphone-symbolic',
            style_class: 'system-status-icon',
        }));

    }

    _startVoiceTyping() {
        const apiKey = this.settings.get_string('openai-api-key');
        const apiUrl = this.settings.get_string('openai-api-url');

        if (!apiKey) {
            Main.notify(_('Voice Typing'), _('Please configure your OpenAI API key in settings'));
            return;
        }

        Main.notify(_('Voice Typing'), _('Starting voice transcription...'));
        // TODO: Implement actual voice typing functionality
    }
});

export default class VoiceTypingExtension extends Extension {
    enable() {
        this._settings = this.getSettings();

        this._indicator = new Indicator(this._settings);
        Main.panel.addToStatusArea(this.uuid, this._indicator);
        this._indicator.menu.addAction(_('Preferences'), () => {
            this.openPreferences();
        });

        this._settings.connect('changed::openai-api-key', (settings, key) => {
            console.debug(`${key} = ${settings.get_string(key)}`);
        });
        this._settings.connect('changed::openai-api-url', (settings, key) => {
            console.debug(`${key} = ${settings.get_string(key)}`);
        });
    }

    disable() {
        this._indicator.destroy();
        this._indicator = null;
        this._settings = null;
    }
}
