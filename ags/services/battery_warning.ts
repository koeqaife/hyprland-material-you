const battery = await Service.import("battery");

const battery_messages = {
    warnLevels: [15, 5],
    warnTitles: ["Low battery", "Very low battery"],
    warnMessages: ["Plug in the charger", "You there?"]
};

let battery_warned = false;

async function battery_notification() {
    const percent = battery.percent;
    const charging = battery.charging;
    if (charging) {
        battery_warned = false;
        return;
    }
    for (let i = battery_messages.warnLevels.length - 1; i >= 0; i--) {
        if (percent <= battery_messages.warnLevels[i] && !charging && !battery_warned) {
            battery_warned = true;
            Utils.execAsync([
                "bash",
                "-c",
                `notify-send "${battery_messages.warnTitles[i]}" "${battery_messages.warnMessages[i]}" -u critical &`
            ]).catch(print);
            break;
        }
    }
}

export async function start_battery_warning_service() {
    Utils.timeout(1, () => {
        battery.connect("changed", () => battery_notification().catch(print));
    });
}
