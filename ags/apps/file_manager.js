#!/usr/bin/env gjs

const { Gio, Gtk, GObject } = imports.gi;

class FileManager {
    constructor() {
        this.application = new Gtk.Application();
        this.application.connect('activate', this.onActivate.bind(this));
    }

    onActivate() {
        this.window = new Gtk.ApplicationWindow({
            application: this.application,
            title: 'File Manager',
            default_width: 800,
            default_height: 600
        });

        const box = new Gtk.Box({ orientation: Gtk.Orientation.VERTICAL, spacing: 6 });
        this.window.set_child(box);

        const headerBar = new Gtk.HeaderBar({
            title: 'File Manager',
            show_close_button: true
        });
        this.window.set_titlebar(headerBar);

        const fileChooserButton = new Gtk.Button({ label: 'Open Folder' });
        fileChooserButton.connect('clicked', this.onOpenFolder.bind(this));
        headerBar.pack_start(fileChooserButton);

        this.fileListStore = new Gtk.ListStore();
        this.fileListStore.set_column_types([GObject.TYPE_STRING, GObject.TYPE_STRING]);

        this.treeView = new Gtk.TreeView({ model: this.fileListStore });
        box.append(this.treeView);

        const fileNameColumn = new Gtk.TreeViewColumn({ title: 'File Name' });
        const fileNameRenderer = new Gtk.CellRendererText();
        fileNameColumn.pack_start(fileNameRenderer, true);
        fileNameColumn.add_attribute(fileNameRenderer, 'text', 0);
        this.treeView.append_column(fileNameColumn);

        const fileTypeColumn = new Gtk.TreeViewColumn({ title: 'File Type' });
        const fileTypeRenderer = new Gtk.CellRendererText();
        fileTypeColumn.pack_start(fileTypeRenderer, true);
        fileTypeColumn.add_attribute(fileTypeRenderer, 'text', 1);
        this.treeView.append_column(fileTypeColumn);

        this.window.show_all();
    }

    onOpenFolder() {
        const dialog = new Gtk.FileChooserDialog({
            title: 'Open Folder',
            action: Gtk.FileChooserAction.SELECT_FOLDER,
            transient_for: this.window,
            modal: true
        });

        dialog.add_button('Cancel', Gtk.ResponseType.CANCEL);
        dialog.add_button('Open', Gtk.ResponseType.ACCEPT);

        dialog.connect('response', (dialog, response) => {
            if (response === Gtk.ResponseType.ACCEPT) {
                const folder = dialog.get_file();
                this.loadFolder(folder);
            }
            dialog.destroy();
        });

        dialog.show();
    }

    loadFolder(folder) {
        this.fileListStore.clear();

        const enumerator = folder.enumerate_children('standard::name,standard::type', Gio.FileQueryInfoFlags.NONE, null);
        let info;
        while ((info = enumerator.next_file(null)) !== null) {
            const fileName = info.get_name();
            const fileType = info.get_file_type() === Gio.FileType.DIRECTORY ? 'Directory' : 'File';
            this.fileListStore.set(this.fileListStore.append(), [0, 1], [fileName, fileType]);
        }
    }

    run(argv) {
        this.application.run(argv);
    }
}

const app = new FileManager();
app.run(ARGV);
