import { Variable as VariableType } from "types/variable";
import { current_wallpaper } from "variables";

const GLib = imports.gi.GLib;
const Gio = imports.gi.Gio;

const changing = Variable(false);
const changing_state = Variable("init");
const changing_states = {
    init: "Initializing...",
    changing: "Changing wallpaper...",
    colors: "Generating colors...",
    tasks: "Waiting for some tasks to finish...",
    finish: "Finished!"
};
Utils.monitorFile("/tmp/wallpaper.status", () => {
    Utils.readFileAsync("/tmp/wallpaper.status")
        .then((c) => {
            changing_state.setValue(c);
        })
        .catch(() => {});
});
// @ts-ignore
const focused: VariableType<null | string> = Variable(null);

function splitListInHalf<T>(arr: T[]): [T[], T[]] {
    const midPoint = Math.ceil(arr.length / 2);
    const firstPart = arr.slice(0, midPoint);
    const secondPart = arr.slice(midPoint);

    return [firstPart, secondPart];
}

function listFilesByExtensions(directoryPath: string, extensions: string[]): string[] {
    let files: string[] = [];

    let directory = Gio.File.new_for_path(directoryPath);

    let enumerator = directory.enumerate_children("standard::*", Gio.FileQueryInfoFlags.NONE, null);

    let fileInfo;
    while ((fileInfo = enumerator.next_file(null)) !== null) {
        let fileName = fileInfo.get_name();

        for (let ext of extensions) {
            if (fileName.toLowerCase().endsWith(ext.toLowerCase())) {
                files.push(fileName);
                break;
            }
        }
    }

    return files;
}

const Wallpaper = (image: string, name: string) =>
    Widget.Button({
        on_clicked: () => {
            focused.setValue(image);
        },
        class_name: "row wallpaper",
        setup: (self) => {
            self.hook(focused, () => {
                self.toggleClassName("focused", focused.value === image);
            });
        },
        hexpand: true,
        child: Widget.Box({
            children: [
                Widget.Box({
                    hpack: "center",
                    vpack: "center",
                    class_name: "image",
                    setup(self) {
                        const cache_file = `${GLib.get_home_dir()}/.cache/thumbnails/wallpaper/${name}`;
                        Utils.readFileAsync(cache_file).catch(() => {
                            Utils.execAsync(
                                `magick ${image} -resize x32 -gravity Center -extent 1:1 ${cache_file}`
                            ).catch(print);
                        });
                        Utils.idle(() => {
                            self.css = `background-image: url("${cache_file}");`;
                        });
                    }
                }),
                Widget.Box({
                    vertical: true,
                    hexpand: true,
                    vpack: "center",
                    children: [
                        Widget.Label({
                            hpack: "start",
                            class_name: "title",
                            label: name,
                            truncate: "end"
                        })
                        // Widget.Label({
                        //     hpack: "start",
                        //     class_name: "description",
                        //     label: "Idk"
                        // })
                    ]
                })
            ]
        })
    });

function CacheThumbnails() {
    Utils.execAsync(`mkdir -p ${GLib.get_home_dir()}/.cache/thumbnails/wallpaper`).catch(print);
    const original_directory = `${GLib.get_home_dir()}/wallpaper`;
    const extensions = [".jpg", ".jpeg", ".png"];
    const fileList = listFilesByExtensions(original_directory, extensions);
    fileList.forEach((value, index) => {
        const path = `${original_directory}/${value}`;
        const cache_file = `${GLib.get_home_dir()}/.cache/thumbnails/wallpaper/${value}`;
        Utils.idle(() => {
            Utils.readFileAsync(cache_file).catch(() => {
                Utils.execAsync(`magick ${path} -resize x32 -gravity Center -extent 1:1 ${cache_file}`).catch(print);
            });
        });
    });
}

CacheThumbnails();

const WallpaperList = () => {
    const original_directory = `${GLib.get_home_dir()}/wallpaper`;
    const extensions = [".jpg", ".jpeg", ".png"];
    let fileList = listFilesByExtensions(original_directory, extensions);
    let [l_fileList, r_fileList] = splitListInHalf(fileList);
    const box = Widget.Box({
        vertical: false,
        attribute: {
            update: (self) => {
                self.children[0].children! = l_fileList.map((value) =>
                    Wallpaper(`${original_directory}/${value}`, value)
                );
                self.children[1].children! = r_fileList.map((value) =>
                    Wallpaper(`${original_directory}/${value}`, value)
                );
            }
        },
        children: [
            Widget.Box({
                vertical: true,
                children: []
            }),
            Widget.Box({
                vertical: true,
                children: []
            })
        ]
    });

    box.attribute.update(box);

    return box;
};

export function Wallpapers() {
    focused.setValue(current_wallpaper.value);
    const box = Widget.Box({
        vertical: true,
        children: [WallpaperList()]
    });
    return Widget.Box({
        vertical: true,
        children: [
            Widget.Scrollable({
                hscroll: "never",
                child: box,
                vexpand: true
            }),
            Widget.Box({
                class_name: "bottom_bar",
                vertical: true,
                children: [
                    Widget.Box({
                        class_name: "row",
                        visible: changing.bind(),
                        children: [
                            Widget.Label({
                                class_name: "description",
                                label: changing_state.bind().as((state) => changing_states[state])
                            })
                        ]
                    }),
                    Widget.Box({
                        class_name: "actions",
                        hpack: "end",
                        children: [
                            Widget.Button({
                                class_name: "standard_button",
                                label: "Random",
                                hpack: "end",
                                on_clicked: () => {
                                    if (!changing.value) {
                                        changing.setValue(true);
                                        Utils.execAsync(
                                            `python -O ${GLib.get_home_dir()}/dotfiles/hypr/scripts/wallpaper.py -R`
                                        )
                                            .catch(print)
                                            .finally(() => {
                                                changing.setValue(false);
                                            });
                                    }
                                },
                                setup: (self) => {
                                    self.hook(changing, () => {
                                        self.toggleClassName("disabled", changing.value);
                                    });
                                }
                            }),
                            Widget.Button({
                                class_name: "filled_button",
                                label: "Select",
                                hpack: "end",
                                on_clicked: () => {
                                    if (!changing.value) {
                                        changing.setValue(true);
                                        Utils.execAsync(
                                            `python -O ${GLib.get_home_dir()}/dotfiles/hypr/scripts/wallpaper.py -I ${
                                                focused.value
                                            }`
                                        )
                                            .catch(print)
                                            .finally(() => {
                                                changing.setValue(false);
                                            });
                                    }
                                },
                                setup: (self) => {
                                    self.hook(changing, () => {
                                        self.toggleClassName("disabled", changing.value);
                                    });
                                }
                            })
                        ]
                    })
                ]
            })
        ]
    });
}
