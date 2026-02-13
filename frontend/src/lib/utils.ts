import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

/**
 * cn (ClassName) Yardımcısı 🪄
 * 
 * Bu fonksiyon iki süper gücü birleştirir:
 * 1. clsx: Koşullu sınıfları yönetir (örn: isActive && "bg-blue-500")
 * 2. twMerge: Tailwind sınıf çakışmalarını çözer (örn: "p-2" vs "p-4")
 * 
 * Kullanım:
 * className={cn("text-red-500", isError && "font-bold", className)}
 */
export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs))
}
