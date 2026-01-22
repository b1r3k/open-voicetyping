// Copyright (c) 2024-2026 Lukasz Jachym <lukasz.jachym@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later

import Gio from 'gi://Gio';
import GLib from 'gi://GLib';


export class DBusProxy {
    constructor(service, object_path, interface_name) {
        console.debug(`DBusProxy: ${service}, ${object_path}, ${interface_name}`);
        this.proxy = Gio.DBusProxy.new_for_bus_sync(
            Gio.BusType.SYSTEM,
            Gio.DBusProxyFlags.NONE,
            null,
            service,
            object_path,
            interface_name,
            null
        );
    }

    call(methodName, ...args) {
        console.debug(`DBusProxy: call ${methodName} with args ${args}`);

        // For DBus method calls, we need to create a variant tuple
        // If no args, pass null, otherwise create a variant tuple with properly typed variants
        let args_variant;
        if (args.length === 0) {
            args_variant = null;
        } else {
            // Convert arguments to proper variants
            const variantArgs = args.map(arg => {
                if (typeof arg === 'string') {
                    return GLib.Variant.new_string(arg);
                } else if (typeof arg === 'number') {
                    return GLib.Variant.new_int32(arg);
                } else if (typeof arg === 'boolean') {
                    return GLib.Variant.new_boolean(arg);
                } else {
                    // For other types, try to create a variant directly
                    return GLib.Variant.new_variant(arg);
                }
            });
            args_variant = GLib.Variant.new_tuple(variantArgs);
        }

        return this.proxy.call_sync(methodName, args_variant, Gio.DBusCallFlags.NONE, -1, null);
    }

    connectSignal(signalName, callback) {
        return this.proxy.connect('g-signal', (proxy, senderName, signalNameReceived, parameters) => {
            if (signalNameReceived === signalName) {
                callback(parameters);
            }
        });
    }

    connectSignalWithRetry(signalName, callback, maxRetries = 3) {
        let attempts = 0;
        const connect = () => {
            try {
                return this.connectSignal(signalName, callback);
            } catch (error) {
                attempts++;
                if (attempts < maxRetries) {
                    console.warn(`Signal connection failed, retry ${attempts}/${maxRetries}`);
                    GLib.timeout_add(GLib.PRIORITY_DEFAULT, 1000, () => {
                        connect();
                        return GLib.SOURCE_REMOVE;
                    });
                } else {
                    console.error(`Failed to connect signal after ${maxRetries} attempts`);
                }
                return null;
            }
        };
        return connect();
    }

    disconnectSignal(handlerId) {
        this.proxy.disconnect(handlerId);
    }
}
