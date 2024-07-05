import { Binding } from "types/service";
const GLib = imports.gi.GLib;
import { cpu_cores, cpu_name, kernel_name, amount_of_ram, gpu_name, hostname, current_os, cur_uptime } from "variables";

type StringOrBinding = string | Binding<any, any, string> | null;

const empty_func = () => {};

const Row = (
    title: StringOrBinding,
    description: StringOrBinding,
    on_primary_click: any = empty_func,
    on_secondary_click: any = empty_func
) =>
    Widget.EventBox({
        class_name: "row",
        on_primary_click_release: on_primary_click,
        on_secondary_click_release: on_secondary_click,
        child: Widget.Box({
            class_name: "row",
            vpack: "start",
            children: [
                Widget.Box({
                    vertical: true,
                    hexpand: true,
                    vpack: "center",
                    hpack: "start",
                    children: [
                        Widget.Label({
                            hpack: "start",
                            class_name: "title",
                            label: title
                        }),
                        Widget.Label({
                            hpack: "start",
                            class_name: "description",
                            label: description
                        })
                    ]
                })
            ]
        })
    });

const repo_link = "https://github.com/koeqaife/hyprland-material-you";
const current_de = GLib.getenv("DESKTOP_SESSION");

export function Info() {
    const box = Widget.Box({
        vertical: true,
        children: [
            Row("Dotfiles", "Material You"),
            Row("Author", "mrdan__ (Discord)"),
            Row("Repo", repo_link, () => {
                Utils.execAsync(`xdg-open "${repo_link}"`).catch(print);
            }),
            Widget.Separator(),
            Row("DE", current_de!),
            Row("OS", current_os),
            Row("Kernel", kernel_name),
            Row("Uptime", cur_uptime.bind()),
            Row("CPU", `${cpu_name} (${cpu_cores} Cores)`),
            Row("GPU", `${gpu_name}`),
            Row("Ram", amount_of_ram),
            Row("Hostname", hostname)
        ]
    });
    return Widget.Scrollable({
        hscroll: "never",
        child: box,
        vexpand: true
    });
}
