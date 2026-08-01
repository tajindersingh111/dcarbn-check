"use client";

import type { ReactNode } from "react";

import { CloseIcon } from "@/components/icons";

export function Modal({
  open,
  title,
  description,
  onClose,
  children
}: {
  open: boolean;
  title: string;
  description: string;
  onClose: () => void;
  children: ReactNode;
}) {
  if (!open) {
    return null;
  }
  return (
    <div className="modal-backdrop" role="presentation">
      <section
        aria-describedby="modal-description"
        aria-labelledby="modal-title"
        aria-modal="true"
        className="modal"
        role="dialog"
      >
        <header className="modal-header">
          <div>
            <h2 id="modal-title">{title}</h2>
            <p id="modal-description">{description}</p>
          </div>
          <button
            aria-label="Close dialog"
            className="icon-button"
            onClick={onClose}
            type="button"
          >
            <CloseIcon />
          </button>
        </header>
        {children}
      </section>
    </div>
  );
}
