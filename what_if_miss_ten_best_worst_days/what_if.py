import argparse
import csv
from collections import namedtuple

from typing import Dict, List


# Header for historical price data downloaded from Yahoo Finance.
CSV_FIELD_NAMES = ["date", "open", "high", "low", "close", "adj close", "volume"]

# Checks whether given data format matches assumptions.
def validate_header(header_row: Dict[str, str]):
    for expected_name, actual_name in header_row.items():
        lower_actual_name = actual_name.lower()
        if expected_name != lower_actual_name:
            raise ValueError(
                f"Expecting column '{expected_name}', got `{lower_actual_name}`, "
                "please make sure the historical price file was downloaded from Yahoo Finance"
            )


DayPerf = namedtuple("DayPerf", ["date", "change_percentage"])

# Find the n best days for price increase, returns list of DayPerf for those days.
def find_days(data_dict_reader: csv.DictReader, n: int = 10, find_best: bool = True) -> List[DayPerf]:
    chosen_days: List[DayPerf] = []

    if n == 0:
        return chosen_days

    # Special case for first day
    first_day = next(data_dict_reader)
    change_absolute_value = float(first_day["close"]) - float(first_day["open"])
    change_percentage = change_absolute_value / float(first_day["open"])
    chosen_days.append(
        DayPerf(first_day["date"], change_percentage)
    )
    last_closing_price = float(first_day["open"])

    # Fill up best_days with first n days
    for _ in range(n - 1):
        day = next(data_dict_reader)
        change_absolute_value = float(day["close"]) - last_closing_price
        change_percentage = change_absolute_value / last_closing_price
        last_closing_price = float(day["close"])
        chosen_days.append(DayPerf(day["date"], change_percentage))

    # Go through all days to find the best/worst
    for day in data_dict_reader:
        change_absolute_value = float(day["close"]) - last_closing_price
        change_percentage = (
            float(day["close"]) - last_closing_price
        ) / last_closing_price
        last_closing_price = float(day["close"])

        # Skip days when performance isn't in top n days
        if find_best:
            if change_percentage < chosen_days[-1].change_percentage:
                continue
        else:
            if change_percentage > chosen_days[-1].change_percentage:
                continue

        chosen_days.append(DayPerf(day["date"], change_percentage))
        chosen_days.sort(key=lambda x: x[1], reverse=find_best)
        chosen_days.pop()

    return chosen_days

# Return performance of a security if certain days are missed in trading
def perf_if_missing_days(data_dict_reader: csv.DictReader, missed_days: List[DayPerf]):
    # Special case for first day
    first_day = next(data_dict_reader)
    open_price = float(first_day["open"])
    last_close_price = float(first_day["close"])

    missed_days_dates = set([missed_day.date for missed_day in missed_days])

    value = 0 
    missed_yesterday = False
    for day in data_dict_reader:
        date = day["date"]
        # Simulating buying at the beginning of the day after missed_day
        if missed_yesterday and not date in missed_days_dates:
            value = value - float(day["open"])

        missed_yesterday = False

        # Simulating selling at end of the day before missed_day
        if date in missed_days_dates:
            value = value + last_close_price
            missed_yesterday = True

        last_close_price = float(day["close"])

    value = value + last_close_price

    total_changed_value = last_close_price - open_price
    total_changed_percentage = total_changed_value / open_price

    changed_value_if_missing_days = value - open_price
    changed_percentage_if_missing_days = changed_value_if_missing_days / open_price

    print(f"If you hold throughout given period, your performance will be: {total_changed_percentage:.2%}")
    print(f"If you miss these days, your performance will be: {changed_percentage_if_missing_days:.2%}")

def analyze(file_name: str, num_best_days_to_miss: int, num_worst_days_to_miss: int):
    # First find ten best trading days and see what happens if you miss them
    with open(file_name) as f:
        data_dict_reader = csv.DictReader(f, fieldnames=CSV_FIELD_NAMES)

        # Skip header and validate format
        header = next(data_dict_reader)
        validate_header(header_row=header)

        best_days = find_days(data_dict_reader, n=num_best_days_to_miss, find_best=True)

        # Reset file and skip header
        f.seek(0)
        _ = next(data_dict_reader)
        worst_days = find_days(data_dict_reader, n=num_worst_days_to_miss, find_best=False)

        days_to_miss = best_days + worst_days

        # Reset file and skip header
        f.seek(0)
        _ = next(data_dict_reader)
        perf_if_missing_days(data_dict_reader, days_to_miss)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Compute what happens if you time the stock market."
    )
    parser.add_argument(
        "--file",
        type=str,
        help="Full path to find historical trading data of a security from Yahoo Finance",
        required=True,
    )
    parser.add_argument(
        "--num_best_days_to_miss",
        type=int,
        help="Number of best trading days to miss",
        default=10,
    )
    parser.add_argument(
        "--num_worst_days_to_miss",
        type=int,
        help="Number of worst trading days to miss",
        default=0,
    )
    args = parser.parse_args()
    analyze(args.file, args.num_best_days_to_miss, args.num_worst_days_to_miss)
