import { useEffect, useRef, useState } from "react";
import type { AuthTokenPair } from "../lib/backend";
import AuthPanel from "./AuthPanel";

interface SaveRelationSheetProps {
  email: string;
  onAuthenticated: (tokens: AuthTokenPair) => void;
  onLoggedOut: () => void;
  onClose: () => void;
}

export default function SaveRelationSheet({
  email,
  onAuthenticated,
  onLoggedOut,
  onClose,
}: SaveRelationSheetProps) {
  const [stage, setStage] = useState<"intro" | "account">(email ? "account" : "intro");
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    closeButtonRef.current?.focus();
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [onClose]);

  return (
    <div
      className="relation-sheet-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section
        className="relation-sheet"
        role="dialog"
        aria-modal="true"
        aria-label={stage === "account" ? "保存你和小满的关系" : undefined}
        aria-labelledby={stage === "intro" ? "relation-sheet-title" : undefined}
      >
        <div className="relation-sheet-handle" aria-hidden="true" />
        <button
          ref={closeButtonRef}
          type="button"
          className="relation-sheet-close"
          aria-label="关闭保存关系窗口"
          onClick={onClose}
        >
          ×
        </button>

        {stage === "intro" ? (
          <>
            <p className="soft-eyebrow">SAVE YOUR STORY</p>
            <h2 id="relation-sheet-title">把你和小满的故事好好保存下来</h2>
            <p className="relation-sheet-lead">
              注册或登录后，换浏览器、换手机，她也会记得你们聊过的事。
            </p>
            <ul className="relation-benefits">
              <li>保存聊天、记忆和成长节点</li>
              <li>同步失败时，本机记录仍会保留</li>
              <li>家长只能看摘要，不会看到聊天原文</li>
            </ul>
            <button
              type="button"
              className="relation-primary-button"
              onClick={() => setStage("account")}
            >
              保存这段关系
            </button>
            <button type="button" className="relation-text-button" onClick={onClose}>
              先继续聊
            </button>
          </>
        ) : (
          <AuthPanel
            email={email}
            presentation="sheet"
            onAuthenticated={onAuthenticated}
            onLoggedOut={onLoggedOut}
            onFinished={onClose}
          />
        )}
      </section>
    </div>
  );
}
