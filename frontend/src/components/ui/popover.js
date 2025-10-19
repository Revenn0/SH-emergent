import * as React from "react";
import * as RadixPopover from "@radix-ui/react-popover";
import { cn } from "@/lib/utils";

export const Popover = RadixPopover.Root;
export const PopoverTrigger = RadixPopover.Trigger;

export function PopoverContent({ className, align = "center", sideOffset = 8, ...props }) {
  return (
    <RadixPopover.Portal>
      <RadixPopover.Content
        align={align}
        sideOffset={sideOffset}
        className={cn(
          "z-50 w-auto rounded-md border bg-popover p-2 text-popover-foreground shadow-md outline-none",
          className
        )}
        {...props}
      />
    </RadixPopover.Portal>
  );
}
