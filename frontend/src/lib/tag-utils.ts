/**
 * Tag badge styling utilities
 *
 * Single source of truth for tag-related colors and styling
 * across the application.
 */

/**
 * Known tag types used by the application
 */
export type TagName = "dub" | "semi-dub" | "wrong-dub";

/**
 * Returns the Tailwind CSS classes for a tag badge based on the tag name.
 *
 * @param tagName - The name of the tag (dub, semi-dub, wrong-dub, or undefined)
 * @returns CSS classes for the badge styling
 *
 * @example
 * ```tsx
 * <Badge className={getTagBadgeClass("dub")}>dub</Badge>
 * ```
 */
export function getTagBadgeClass(tagName?: string): string {
  switch (tagName) {
    case "dub":
      return "bg-green-500 hover:bg-green-600";
    case "semi-dub":
      return "bg-yellow-500 hover:bg-yellow-600";
    case "wrong-dub":
      return "bg-red-500 hover:bg-red-600";
    default:
      return "";
  }
}
