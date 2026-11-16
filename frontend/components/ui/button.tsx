import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";
const buttonVariants = cva("inline-flex min-h-12 items-center justify-center gap-3 rounded-sm px-6 py-3 text-sm font-semibold transition-colors focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-orange disabled:pointer-events-none disabled:opacity-50", { variants: { variant: { default: "bg-orange text-midnight hover:bg-[#df3d18]", outline: "border border-stone bg-transparent text-midnight hover:bg-midnight hover:text-silver" } }, defaultVariants: { variant: "default" } });
export function Button({ className, variant, ...props }: React.ComponentProps<"button"> & VariantProps<typeof buttonVariants>) { return <button className={cn(buttonVariants({variant, className}))} {...props} />; }
