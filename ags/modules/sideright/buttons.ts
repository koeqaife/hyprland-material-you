// by koeqaife ;)

import { MaterialIcon } from "icons";

const { GLib } = imports.gi;

const scripts_dir = `${GLib.get_home_dir()}/dotfiles/hypr/scripts`;
const lock_command = `${scripts_dir}/lock.sh`;
const logout_command = `${scripts_dir}/exit.sh`;
const shutdown_command = `${scripts_dir}/shutdown.sh`;
const reboot_command = `${scripts_dir}/reboot.sh`;
const suspend_command = `${scripts_dir}/suspend.sh`;

function Button({ icon, command, tooltip, ...props }) {
    let clickCount = 0;
    const button = Widget.Button({
        tooltip_text: tooltip,
        child: MaterialIcon(icon, "20px"),
        class_name: "outline_button",
        on_clicked: (self) => {
            clickCount++;
            if (clickCount === 2) {
                Utils.execAsync(command).catch(print);
                clickCount = 0;
            }
        },
        ...props
    });

    button.connect("focus-out-event", () => {
        clickCount = 0;
    });

    return button;
}

export function Buttons() {
    return Widget.Box({
        class_name: "sidebar_buttons",
        hexpand: true,
        spacing: 5,
        children: [
            Button({
                icon: "lock",
                command: lock_command,
                tooltip: "Lock",
                hexpand: true
            }),
            Button({
                icon: "clear_night",
                command: suspend_command,
                tooltip: "Suspend",
                hexpand: true
            }),
            Button({
                icon: "logout",
                command: logout_command,
                tooltip: "Logout",
                hexpand: true
            }),
            Button({
                icon: "restart_alt",
                command: reboot_command,
                tooltip: "Reboot",
                hexpand: true
            }),
            Button({
                icon: "power_settings_new",
                command: shutdown_command,
                tooltip: "Shutdown",
                hexpand: true
            })
        ]
    });
}
