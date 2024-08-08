const { Box, Button, Label } = Widget;
import { MaterialIcon } from "icons.ts";

import { get_calendar_layout } from "./misc/calendar_layout.js";
import popupwindow from "./misc/popupwindow.ts";

const WINDOW_NAME: string = "calendar";

type CalendarDay = {
    day: string;
    today: number;
};

let calendar_json: CalendarDay[][] = get_calendar_layout(undefined, true);
let month_shift: number = 0;

function get_date_in_x_months_time(x: number): Date {
    const currentDate: Date = new Date();
    let targetMonth: number = currentDate.getMonth() + x;
    let targetYear: number = currentDate.getFullYear();

    targetYear += Math.floor(targetMonth / 12);
    targetMonth = ((targetMonth % 12) + 12) % 12;

    const targetDate: Date = new Date(targetYear, targetMonth, 1);

    return targetDate;
}

const week_days: CalendarDay[] = [
    { day: "Mo", today: 0 },
    { day: "Tu", today: 0 },
    { day: "We", today: 0 },
    { day: "Th", today: 0 },
    { day: "Fr", today: 0 },
    { day: "Sa", today: 0 },
    { day: "Su", today: 0 }
];

const calendar_day = (day: string, today: number) =>
    Widget.Button({
        class_name: `calendar_button ${today == 1 ? "today" : today == -1 ? "othermonth" : ""}`,
        child: Widget.Overlay({
            child: Box({
                class_name: "overlay_box"
            }),
            overlays: [
                Label({
                    hpack: "center",
                    label: String(day)
                })
            ]
        })
    });

const calendar_widget = () => {
    const month_year = Widget.Button({
        class_name: "calendar_monthyear",
        on_clicked: (): void => shift_x_months(0),
        setup: (button: any): void => {
            button.label = `${new Date().toLocaleString("default", { month: "long" })} ${new Date().getFullYear()}`;
        }
    });

    const add_children = (box: ReturnType<typeof Box>, calendar_json: CalendarDay[][]): void => {
        const children = box.get_children();
        for (let i = 0; i < children.length; i++) {
            const child: any = children[i];
            child.destroy();
        }
        box.children = calendar_json.map((row, i) =>
            Widget.Box({
                spacing: 5,
                children: row.map((day, i) => calendar_day(day.day, day.today))
            })
        );
    };

    function shift_x_months(x: number): void {
        if (x == 0) month_shift = 0;
        else month_shift += x;

        const new_date: Date = month_shift == 0 ? new Date() : get_date_in_x_months_time(month_shift);

        calendar_json = get_calendar_layout(new_date, month_shift == 0);
        month_year.label = `${month_shift == 0 ? "" : "• "}${new_date.toLocaleString("default", {
            month: "long"
        })} ${new_date.getFullYear()}`;
        add_children(calendar_days, calendar_json);
    }

    const calendar_header = Widget.Box({
        class_name: "calendar_header",
        spacing: 5,
        setup: (box: any): void => {
            box.pack_start(month_year, false, false, 0);
            box.pack_end(
                Widget.Box({
                    spacing: 5,
                    children: [
                        Button({
                            class_name: "calendar_month_shift standard_icon_button",
                            on_clicked: () => shift_x_months(-1),
                            child: MaterialIcon("chevron_left", "20px")
                        }),
                        Button({
                            class_name: "calendar_month_shift standard_icon_button",
                            on_clicked: () => shift_x_months(1),
                            child: MaterialIcon("chevron_right", "20px")
                        })
                    ]
                }),
                false,
                false,
                0
            );
        }
    });

    const calendar_days = Widget.Box({
        hexpand: true,
        vertical: true,
        spacing: 5,
        setup: (box: any): void => {
            add_children(box, calendar_json);
        }
    });

    return Widget.EventBox({
        on_scroll_up: (): void => shift_x_months(-1),
        on_scroll_down: (): void => shift_x_months(1),
        child: Widget.Box({
            hpack: "center",
            class_name: "calendar_widget",
            children: [
                Widget.Box({
                    hexpand: true,
                    vertical: true,
                    spacing: 5,
                    children: [
                        calendar_header,
                        Widget.Box({
                            homogeneous: true,
                            spacing: 5,
                            children: week_days.map((day, i) => calendar_day(day.day, day.today))
                        }),
                        calendar_days
                    ]
                })
            ]
        })
    });
};

export const calendar = popupwindow({
    name: WINDOW_NAME,
    class_name: "calendar",
    visible: false,
    keymode: "exclusive",
    child: calendar_widget(),
    anchor: ["top", "right"]
});
