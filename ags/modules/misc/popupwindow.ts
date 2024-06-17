import App from 'resource:///com/github/Aylur/ags/app.js';
import Widget from 'resource:///com/github/Aylur/ags/widget.js';
const { Gtk, GLib } = imports.gi;

export default ({
    name,
    child,
    showClassName = "",
    hideClassName = "",
    ...props
}) => {
    return Widget.Window({
        name,
        visible: false,
        type: Gtk.WindowType.POPUP,
        layer: 'overlay',
        resizable: true,
        ...props,
        setup: (self) => {
            self.keybind("Escape", () => App.closeWindow(name));
            if (showClassName != "" && hideClassName !== "") {
                self.hook(App, (self, currentName, visible) => {
                    if (currentName === name) {
                        self.toggleClassName(hideClassName, !visible);
                    }
                });

                if (showClassName !== "" && hideClassName !== "")
                    self.class_name = `${showClassName} ${hideClassName}`;
            }
        },
        child: child,
    });
}