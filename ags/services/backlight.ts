class BrightnessService extends Service {
    static {
        Service.register(
            this,
            {
                "screen-changed": ["float"]
            },
            {
                "screen-value": ["float", "rw"]
            }
        );
    }

    #interface = Utils.exec("sh -c 'ls -w1 /sys/class/backlight | head -1'");

    #screenValue = 0;
    #max = Number(Utils.exec("brightnessctl max"));
    #brightness_file = `/sys/class/backlight/${this.#interface}/brightness`;

    get screen_value() {
        return this.#screenValue;
    }

    set screen_value(percent) {
        if (percent < 0) percent = 0;

        if (percent > 1) percent = 1;

        Utils.execAsync(`brightnessctl set ${percent * 100}% -q`);
    }

    constructor() {
        super();

        Utils.monitorFile(this.#brightness_file, () => this.#onChange());

        this.#onChange();
    }

    async #onChange() {
        this.#screenValue = Number(await Utils.readFileAsync(this.#brightness_file)) / this.#max;

        this.emit("changed");
        this.notify("screen-value");

        this.emit("screen-changed", this.#screenValue);
    }
}

const service = new BrightnessService();

export default service;
