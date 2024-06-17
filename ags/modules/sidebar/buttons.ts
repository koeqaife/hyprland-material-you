const { Gtk, GLib } = imports.gi;

const scripts_dir = `${GLib.get_home_dir()}/dotfiles/hypr/scripts`
const lock_command = `${scripts_dir}/lock.sh`;
const logout_command = `${scripts_dir}/exit.sh`;
const shutdown_command = `${scripts_dir}/shutdown.sh`;
const reboot_command = `${scripts_dir}/reboot.sh`;
const suspend_command = `${scripts_dir}/suspend.sh`;

function LockButton({ icon, ...props }) {
    let clickCount = 0;
    let button = Widget.Button({
        tooltip_text: "Lock",
        child: Widget.Label({
            label: icon,
            class_name: "awesome_icon"
        }),
        class_name: "outline_button",
        ...props,
    })

    button.connect('clicked', () => {
        clickCount++;
        if (clickCount === 2) {
            Utils.execAsync(lock_command).catch(print);
            clickCount = 0;
        }
    });

    button.connect('focus-out-event', () => {
        clickCount = 0;
    });

    return button
}


function SuspendButton({ icon, ...props }) {
    let clickCount = 0;
    let button = Widget.Button({
        tooltip_text: "Suspend",
        child: Widget.Label({
            label: icon,
            class_name: "awesome_icon"
        }),
        class_name: "outline_button",
        ...props,
    })

    button.connect('clicked', () => {
        clickCount++;
        if (clickCount === 2) {
            Utils.execAsync(`mpc -q pause`).catch();
            Utils.execAsync(`playerctl pause`).catch();
            Utils.execAsync(suspend_command).catch();
            clickCount = 0;
        }
    });

    button.connect('focus-out-event', () => {
        clickCount = 0;
    });

    return button
}


function LogoutButton({ icon, ...props }) {
    let clickCount = 0;
    let button = Widget.Button({
        tooltip_text: "Logout",
        child: Widget.Label({
            label: icon,
            class_name: "awesome_icon"
        }),
        class_name: "outline_button",
        ...props,
    })

    button.connect('clicked', () => {
        clickCount++;
        if (clickCount === 2) {
            Utils.execAsync(logout_command).catch();
            clickCount = 0;
        }
    });

    button.connect('focus-out-event', () => {
        clickCount = 0;
    });

    return button
}


function RebootButton({ icon, ...props }) {
    let clickCount = 0;
    let button = Widget.Button({
        tooltip_text: "Reboot",
        child: Widget.Label({
            label: icon,
            class_name: "awesome_icon"
        }),
        class_name: "outline_button",
        ...props,
    })

    button.connect('clicked', () => {
        clickCount++;
        if (clickCount === 2) {
            Utils.execAsync(reboot_command).catch();
            clickCount = 0;
        }
    });

    button.connect('focus-out-event', () => {
        clickCount = 0;
    });

    return button
}


function ShutdownButton({ icon, ...props }) {
    let clickCount = 0;
    let button = Widget.Button({
        tooltip_text: "Shutdown",
        child: Widget.Label({
            label: icon,
            class_name: "awesome_icon"
        }),
        class_name: "outline_button",
        ...props,
    })

    button.connect('clicked', () => {
        clickCount++;
        if (clickCount === 2) {
            Utils.execAsync(shutdown_command).catch();
            clickCount = 0;
        }
    });

    button.connect('focus-out-event', () => {
        clickCount = 0;
    });

    return button
}


export function Buttons() {
    return Widget.Box({
        class_name: "sidebar_buttons",
        hexpand: true,
        spacing: 5,
        children: [
            LockButton({
                icon: "",
                hexpand: true,
            }),
            SuspendButton({
                icon: "",
                hexpand: true,
            }),
            LogoutButton({
                icon: "",
                hexpand: true,
            }),
            RebootButton({
                icon: "",
                hexpand: true,
            }),
            ShutdownButton({
                icon: "",
                hexpand: true,
            })
        ]
    })
}