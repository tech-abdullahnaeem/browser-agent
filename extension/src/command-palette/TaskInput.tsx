/* ── TaskInput — Natural language task input field ── */

import { useState, useRef, useEffect, type KeyboardEvent } from "react";

interface TaskInputProps {
  onSubmit: (task: string) => void;
  disabled?: boolean;
  placeholder?: string;
  autoFocus?: boolean;
}

export function TaskInput({
  onSubmit,
  disabled = false,
  placeholder = "What should I do?",
  autoFocus = true,
}: TaskInputProps) {
  const [value, setValue] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (autoFocus) {
      // Small delay to ensure DOM is ready (especially in Shadow DOM)
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [autoFocus]);

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === "Enter" && value.trim() && !disabled) {
      onSubmit(value.trim());
      setValue("");
    }
  };

  return (
    <div className="relative">
      <input
        ref={inputRef}
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        placeholder={placeholder}
        className="
          w-full px-4 py-3 bg-surface-light border border-border rounded-xl
          text-text-primary placeholder:text-text-muted
          focus:outline-none focus:ring-2 focus:ring-brand-500/50 focus:border-brand-500/50
          disabled:opacity-50 disabled:cursor-not-allowed
          text-sm transition-all
        "
        autoComplete="off"
        spellCheck={false}
      />
      {value.trim() && (
        <div className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted text-xs">
          ↵ Enter
        </div>
      )}
    </div>
  );
}
