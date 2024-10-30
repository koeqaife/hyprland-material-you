// by koeqaife ;)

const battery = await Service.import("battery");

const battery_messages = {
    warnLevels: [15, 5, 1],
    warnTitles: ["Low battery", "Very low battery", "Critical Battery"],
    warnMessages: ["Plug in the charger", "Please plug in the charger", "Your PC is about to shut down"]
};

let last_warning = 101;

async function notifyUser(index) {
    Utils.execAsync([
        "bash",
        "-c",
        `notify-send "${battery_messages.warnTitles[index]}" "${battery_messages.warnMessages[index]}" -u critical &`
    ]).catch(print);
}

async function battery_notification() {
    const percent = battery.percent;
    const charging = battery.charging;
    if (charging) {
        last_warning = 101;
        return;
    }

    const warningLevel = battery_messages.warnLevels
        .slice()
        .reverse()
        .find((level) => percent <= level && last_warning > level);

    if (warningLevel !== undefined) {
        const index = battery_messages.warnLevels.indexOf(warningLevel);
        last_warning = percent;
        await notifyUser(index);
    }
}

export async function start_battery_warning_service() {
    Utils.timeout(1, () => {
        battery_notification().catch(print);
        battery.connect("changed", () => battery_notification().catch(print));
    });
}
