import { toast as sonnerToast } from "sonner";

/**
 * Toast notification utilities
 * Wraps sonner to provide consistent styling and behavior
 */
export const toast = {
  success: (message: string) => {
    sonnerToast.success(message);
  },

  error: (message: string) => {
    sonnerToast.error(message);
  },

  info: (message: string) => {
    sonnerToast.info(message);
  },

  warning: (message: string) => {
    sonnerToast.warning(message);
  },

  /**
   * Show a loading toast that can be updated to success/error
   */
  promise: <T>(
    promise: Promise<T>,
    messages: {
      loading: string;
      success: string;
      error: string | ((error: unknown) => string);
    },
  ) => {
    return sonnerToast.promise(promise, messages);
  },
};
