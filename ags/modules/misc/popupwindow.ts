import App from "resource:///com/github/Aylur/ags/app.js";
import Widget from "resource:///com/github/Aylur/ags/widget.js";
import { WindowProps, Window } from "types/widgets/window";
import Gtk from "gi://Gtk?version=3.0";

type _WindowProps = WindowProps<any, unknown, Window<any, unknown>> | undefined[];

type Type = {
    name: string;
    child: any;
    showClassName?: string;
    hideClassName?: string;
};

export default <T extends Type>({
    name,
    child,
    showClassName = "",
    hideClassName = "",
    ...props
}: T & Omit<_WindowProps, keyof Type>) => {
    return Widget.Window({
        name,
        visible: false,
        type: Gtk.WindowType.POPUP,
        layer: "overlay",
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

                if (showClassName !== "" && hideClassName !== "") self.class_name = `${showClassName} ${hideClassName}`;
            }
        },
        child: child
    });
};
