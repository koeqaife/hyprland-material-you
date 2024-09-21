export default new (class Inhibit extends Service {
    static {
        Service.register(this, {}, { "is-inhibit": ["boolean", "r"] });
    }

    constructor() {
        super();
        this.#id = undefined;
    }

    #id;

    get is_inhibit() {
        return this.#id !== undefined;
    }

    #inhibit(command, data) {
        const output = Utils.exec(
            `dbus-send --print-reply --dest=org.freedesktop.ScreenSaver /org/freedesktop/ScreenSaver org.freedesktop.ScreenSaver.${command} ${data}`
        );

        if (command === "Inhibit") {
            const match = output.match(/uint32\s+(\d+)/);
            return match ? Number(match[1]) : undefined;
        }
        return undefined;
    }

    toggle() {
        if (this.#id === undefined) {
            this.#id = this.#inhibit("Inhibit", "string:'ags' string:'Manual pause'");
        } else {
            this.#id = this.#inhibit("UnInhibit", `uint32:${this.#id}`);
        }
        this.changed("is-inhibit");
    }
})();
