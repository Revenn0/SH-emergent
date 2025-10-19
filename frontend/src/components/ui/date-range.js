import * as React from "react";
import { DayPicker } from "react-day-picker";
import { cn } from "@/lib/utils";

export function DateRangePicker({ value, onChange, className }) {
  // value: { from?: Date, to?: Date }
  return (
    <div className={cn("p-2 bg-white dark:bg-gray-800 rounded-md border border-gray-200 dark:border-gray-700", className)}>
      <DayPicker
        mode="range"
        selected={value}
        onSelect={onChange}
        numberOfMonths={2}
        showOutsideDays
      />
    </div>
  );
}
