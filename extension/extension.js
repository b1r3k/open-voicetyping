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
import Meta from 'gi://Meta';
import Shell from 'gi://Shell';
import Gio from 'gi://Gio';

import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import { Extension, gettext as _ } from 'resource:///org/gnome/shell/extensions/extension.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';


class DBusProxy {
    constructor(service, object_path, interface_name) {
        console.debug(`DBusProxy: ${service}, ${object_path}, ${interface_name}`);
        this.proxy = Gio.DBusProxy.new_for_bus_sync(
            Gio.BusType.SESSION,
            Gio.DBusProxyFlags.NONE,
            null,
            service,
            object_path,
            interface_name,
            null
        );
    }

    call(methodName) {
        console.debug(`DBusProxy: call ${methodName}`);
        return this.proxy.call_sync(methodName, null, Gio.DBusCallFlags.NONE, -1, null);
    }
}


const Indicator = GObject.registerClass(
    class Indicator extends PanelMenu.Button {
        _init(settings) {
            super._init(0.0, _('Voice Typing'));

            this.settings = settings;

            this.icon = new St.Icon({
                icon_name: 'audio-input-microphone-symbolic',
                style_class: 'system-status-icon',
            });
            this.add_child(this.icon);

        }

        setRecordingState(isRecording) {
            if (isRecording) {
                this.icon.add_style_class_name('recording');
            } else {
                this.icon.remove_style_class_name('recording');
            }
        }

    });

export default class VoiceTypingExtension extends Extension {
    enable() {
        this._shortcutsBindingIds = [];
        this._settings = this.getSettings();
        this._dbusProxy = new DBusProxy('com.cxlab.VoiceTyping', '/com/cxlab/VoiceTyping', 'com.cxlab.VoiceTypingInterface');

        this._indicator = new Indicator(this._settings);
        Main.panel.addToStatusArea(this.uuid, this._indicator);
        this._indicator.menu.addAction(_('Preferences'), () => {
            this.openPreferences();
        });

        // Register global keyboard shortcuts
        this._registerKeyboardShortcuts();

        this._settings.connect('changed::openai-api-key', (settings, key) => {
            console.debug(`${key} = ${settings.get_string(key)}`);
        });
        this._settings.connect('changed::openai-api-url', (settings, key) => {
            console.debug(`${key} = ${settings.get_string(key)}`);
        });
    }

    disable() {
        // Unregister keyboard shortcuts
        this._unregisterKeyboardShortcuts();

        this._indicator.destroy();
        this._indicator = null;
        this._settings = null;
        this._dbusProxy = null;
    }

    _bindShortcut(name, callback) {
        const ModeType = Shell.hasOwnProperty('ActionMode')
            ? Shell.ActionMode
            : Shell.KeyBindingMode;

        console.debug(`Binding shortcut ${name} to ${this._settings.get_strv(name)}`);

        try {
            var ret = Main.wm.addKeybinding(
                name,
                this._settings,
                Meta.KeyBindingFlags.NONE,
                ModeType.ALL,
                callback.bind(this),
            );
            if (ret) {
                console.debug(`Successfully bound shortcut ${name}`);
            } else {
                console.error(`Failed to bind shortcut ${name}`);
            }
        } catch (error) {
            console.error(`Failed to bind shortcut ${name}:`, error);
        }

        this._shortcutsBindingIds.push(name);
    }

    _registerKeyboardShortcuts() {
        this._bindShortcut('shortcut-start-stop', () => this._onShortcutPressed());
    }

    _updateShortcuts() {
        // Unregister old shortcuts
        this._unregisterKeyboardShortcuts();
        // Register new shortcuts
        this._registerKeyboardShortcuts();
    }

    _unregisterKeyboardShortcuts() {
        this._shortcutsBindingIds.forEach((id) => Main.wm.removeKeybinding(id));
        this._shortcutsBindingIds = [];
    }

    _onShortcutPressed() {
        if (this._isRecording) {
            this._stopRecording();
        } else {
            this._startRecording();
        }
    }

    _startRecording() {
        // This would implement the actual hold-to-talk functionality
        // You could start recording here and stop when the key is released
        console.debug('Starting hold recording...');

        // For hold-to-talk, you might want to:
        // 1. Start recording immediately
        // 2. Show a visual indicator that recording is active
        // 3. Stop recording when the key is released

        // Example implementation:
        this._isRecording = true;
        this._indicator.setRecordingState(true);
        this._dbusProxy.call('StartRecording');
    }

    _stopRecording() {
        this._isRecording = false;
        this._indicator.setRecordingState(false);
        this._dbusProxy.call('StopRecording');
    }
}
