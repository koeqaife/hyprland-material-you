function check_leap_year(year) {
    return (
        year % 400 == 0 ||
        (year % 4 == 0 && year % 100 != 0));
}

function month_day(month, year) {
    const leap_year = check_leap_year(year);
    if ((month <= 7 && month % 2 == 1) || (month >= 8 && month % 2 == 0)) return 31;
    if (month == 2 && leap_year) return 29;
    if (month == 2 && !leap_year) return 28;
    return 30;
}

function next_month_days(month, year) {
    const leap_year = check_leap_year(year);
    if (month == 1 && leap_year) return 29;
    if (month == 1 && !leap_year) return 28;
    if (month == 12) return 31;
    if ((month <= 7 && month % 2 == 1) || (month >= 8 && month % 2 == 0)) return 30;
    return 31;
}

function prev_month_days(month, year) {
    const leap_year = check_leap_year(year);
    if (month == 3 && leap_year) return 29;
    if (month == 3 && !leap_year) return 28;
    if (month == 1) return 31;
    if ((month <= 7 && month % 2 == 1) || (month >= 8 && month % 2 == 0)) return 30;
    return 31;
}

export function get_calendar_layout(date_object, highlight) {
    if (!date_object) date_object = new Date();
    const weekday = (date_object.getDay() + 6) % 7;
    const day = date_object.getDate();
    const month = date_object.getMonth() + 1;
    const year = date_object.getFullYear();
    const weekday_of_month_first = (weekday + 35 - (day - 1)) % 7;
    const days_in_month = month_day(month, year);
    const days_in_next_month = next_month_days(month, year);
    const days_in_prev_month = prev_month_days(month, year);

    // Fill
    var month_diff = (weekday_of_month_first == 0 ? 0 : -1);
    var to_fill, dim;
    if(weekday_of_month_first == 0) {
        to_fill = 1;
        dim = days_in_month;
    }
    else {
        to_fill = (days_in_prev_month - (weekday_of_month_first - 1));
        dim = days_in_prev_month;
    }
    var calendar = [...Array(6)].map(() => Array(7));
    var i = 0, j = 0;
    while (i < 6 && j < 7) {
        calendar[i][j] = {
            "day": to_fill,
            "today": ((to_fill == day && month_diff == 0 && highlight) ? 1 : (
                month_diff == 0 ? 0 :
                    -1
            ))
        };
        // Increment
        to_fill++;
        if (to_fill > dim) { // Next month?
            month_diff++;
            if (month_diff == 0)
                dim = days_in_month;
            else if (month_diff == 1)
                dim = days_in_next_month;
            to_fill = 1;
        }
        // Next tile
        j++;
        if (j == 7) {
            j = 0;
            i++;
        }

    }
    return calendar;
}
