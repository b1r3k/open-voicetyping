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

import {ExtensionPreferences, gettext as _} from 'resource:///org/gnome/Shell/Extensions/js/extensions/prefs.js';

import { DBusProxy } from './dbus.js';

import { SchemaKeys } from './const.js';


export default class VoiceTypingPreferences extends ExtensionPreferences {
    async populateInferenceDropdowns(providerCombo, modelCombo) {
        try {
            // Create DBus proxy to connect to the service
            const proxy = new DBusProxy('com.cxlab.VoiceTyping', '/com/cxlab/VoiceTyping', 'com.cxlab.VoiceTypingInterface');

            // Get available inference providers
            const providers = await proxy.call('GetAvailableInferenceProviders');
            const providerList = providers.deepUnpack()[0];
            console.info(`Available inference providers: ${providerList}`);

            // Clear and populate provider combo
            providerCombo.remove_all();
            providerList.forEach(provider => {
                providerCombo.append(provider, provider);
            });

            // Set the saved provider value if it exists
            const settings = this.getSettings();
            const savedProvider = settings.get_string('inference-provider');
            if (savedProvider && providerList.includes(savedProvider)) {
                providerCombo.set_active_id(savedProvider);
            } else if (providerList.length > 0) {
                // Fallback to first available provider if saved one not found
                providerCombo.set_active_id(providerList[0]);
            }

            // Handle provider change to update models
            providerCombo.connect('changed', async () => {
                const selectedProvider = providerCombo.get_active_id();
                if (selectedProvider) {
                    try {
                        // Get available models for selected provider
                        const models = await proxy.call('GetAvailableProviderModels', selectedProvider);
                        const modelList = models.deepUnpack()[0];

                        // Clear and populate model combo
                        modelCombo.remove_all();
                        modelList.forEach(model => {
                            modelCombo.append(model, model);
                        });

                        // After populating models, set the saved model value if it exists
                        const settings = this.getSettings();
                        const savedModel = settings.get_string('inference-model');
                        if (savedModel && modelList.includes(savedModel)) {
                            modelCombo.set_active_id(savedModel);
                        } else if (modelList.length > 0) {
                            // Fallback to first available model if saved one not found
                            modelCombo.set_active_id(modelList[0]);
                        }
                    } catch (error) {
                        console.error('Failed to fetch models for provider:', selectedProvider, error);
                    }
                }
            });

            // Trigger initial model population
            const initialProvider = providerCombo.get_active_id();
            if (initialProvider) {
                providerCombo.emit('changed');
            }

        } catch (error) {
            console.error('Failed to populate inference dropdowns:', error);
        }
    }

    async fillPreferencesWindow(window) {
        // Use the same GSettings schema as in extension.js
        const page = new Adw.PreferencesPage();

        // Add description group
        const descriptionGroup = new Adw.PreferencesGroup({
            title: _('Configuration'),
            description: _('Configure your AI service API credentials to enable voice typing functionality.'),
        });
        page.add(descriptionGroup);

        const group = new Adw.PreferencesGroup();
        page.add(group);

        // Inference Provider dropdown
        const inferenceProviderRow = new Adw.ActionRow({
            title: _('Inference Provider'),
        });
        const inferenceProviderCombo = new Gtk.ComboBoxText();
        inferenceProviderRow.add_suffix(inferenceProviderCombo);
        inferenceProviderRow.activatable_widget = inferenceProviderCombo;
        group.add(inferenceProviderRow);

        // Inference Model dropdown
        const inferenceModelRow = new Adw.ActionRow({
            title: _('Inference Model'),
        });
        const inferenceModelCombo = new Gtk.ComboBoxText();
        inferenceModelRow.add_suffix(inferenceModelCombo);
        inferenceModelRow.activatable_widget = inferenceModelCombo;
        group.add(inferenceModelRow);

        // API Key setting
        const apiKeyRow = new Adw.PasswordEntryRow({
            title: _('OpenAI API Key'),
        });
        group.add(apiKeyRow);

        // Groq API Key setting
        const groqApiKeyRow = new Adw.PasswordEntryRow({
            title: _('Groq API Key'),
        });
        group.add(groqApiKeyRow);

        // Function to update API key field visibility based on selected provider
        const updateApiKeyVisibility = () => {
            const selectedProvider = inferenceProviderCombo.get_active_id();

            // Show OpenAI fields only when OpenAI is selected
            apiKeyRow.set_visible(selectedProvider === 'openai');

            // Show Groq fields only when Groq is selected
            groqApiKeyRow.set_visible(selectedProvider === 'groq');
        };

        // Set initial visibility
        updateApiKeyVisibility();

        // Update visibility when provider changes
        inferenceProviderCombo.connect('changed', updateApiKeyVisibility);

        const transcriptionLangRow = new Adw.EntryRow({
            title: _('Transcription Language'),
        });
        group.add(transcriptionLangRow);

        // Keyboard Shortcuts Group
        const shortcutsGroup = new Adw.PreferencesGroup({
            title: _('Keyboard Shortcuts'),
            description: _('Configure keyboard shortcuts for voice typing functionality.'),
        });
        page.add(shortcutsGroup);

        // Start Voice Typing Shortcut
        const startShortcutRow = new Adw.EntryRow({
            title: _('Start Voice Typing shortcut'),
        });
        shortcutsGroup.add(startShortcutRow);

        // Add Save button
        const saveButton = new Gtk.Button({
            label: _('Save Settings'),
            css_classes: ['suggested-action'],
        });
        group.add(saveButton);

        // Populate inference provider and model dropdowns FIRST
        await this.populateInferenceDropdowns(inferenceProviderCombo, inferenceModelCombo);

        // Bind settings AFTER populating dropdowns
        window._settings = this.getSettings();

        // Bind API Key setting
        window._settings.bind(SchemaKeys.OPENAI_API_KEY, apiKeyRow, 'text',
            GObject.BindingFlags.BIDIRECTIONAL
        );

        // Bind Groq API Key setting
        window._settings.bind(SchemaKeys.GROQ_API_KEY, groqApiKeyRow, 'text',
            GObject.BindingFlags.BIDIRECTIONAL
        );

        // Bind inference provider setting
        window._settings.bind(SchemaKeys.INFERENCE_PROVIDER, inferenceProviderCombo, 'active-id',
            GObject.BindingFlags.BIDIRECTIONAL
        );

        // Bind inference model setting
        window._settings.bind(SchemaKeys.INFERENCE_MODEL, inferenceModelCombo, 'active-id',
            GObject.BindingFlags.BIDIRECTIONAL
        );

        // Bind language setting
        window._settings.bind(SchemaKeys.TRANSCRIPTION_LANGUAGE, transcriptionLangRow, 'text',
            GObject.BindingFlags.BIDIRECTIONAL
        );

        // Handle shortcut changes manually since we can't bind directly
        startShortcutRow.connect('changed', () => {
            const shortcutText = startShortcutRow.get_text();
            if (shortcutText) {
                window._settings.set_strv('shortcut-start-stop', [shortcutText]);
            }
        });

        // Load current shortcut value
        const currentShortcuts = window._settings.get_strv('shortcut-start-stop');
        if (currentShortcuts.length > 0) {
            startShortcutRow.set_text(currentShortcuts[0]);
        }

        // Save button handler
        saveButton.connect('clicked', () => {
            const apiKey = apiKeyRow.get_text();
            const groqApiKey = groqApiKeyRow.get_text();
            const transcriptionLang = transcriptionLangRow.get_text();
            const startShortcut = startShortcutRow.get_text();
            const inferenceProvider = inferenceProviderCombo.get_active_id();
            const inferenceModel = inferenceModelCombo.get_active_id();

            window._settings.set_string(SchemaKeys.OPENAI_API_KEY, apiKey);
            window._settings.set_string(SchemaKeys.GROQ_API_KEY, groqApiKey);
            window._settings.set_string(SchemaKeys.TRANSCRIPTION_LANGUAGE, transcriptionLang);
            window._settings.set_string(SchemaKeys.INFERENCE_PROVIDER, inferenceProvider);
            window._settings.set_string(SchemaKeys.INFERENCE_MODEL, inferenceModel);
            if (startShortcut) {
                window._settings.set_strv('shortcut-start-stop', [startShortcut]);
            }

            console.debug('Settings saved - OpenAI API Key:', apiKey);
            console.debug('Groq API Key:', groqApiKey);
            console.debug('Inference Provider:', inferenceProvider, 'Inference Model:', inferenceModel);
            console.debug('Shortcuts - Start:', startShortcut);
        });

        window.add(page);
    }
}
