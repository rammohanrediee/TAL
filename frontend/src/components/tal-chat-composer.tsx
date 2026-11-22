"use client";

import { useCallback, useEffect, useState } from "react";
import {
  ChatComposer,
  ChatSendButton,
} from "@astryxdesign/core/Chat";
import {
  ChatComposerAttachButton,
  ChatComposerAttachments,
  LocalChatComposerProvider,
  useChatComposer,
} from "@/components/ui/chat-composer";
import styles from "./chat-workspace.module.css";

const RESUME_ACCEPT = ".pdf,.docx";
const RESUME_MAX_BYTES = 5 * 1024 * 1024;

type TalChatComposerProps = {
  id?: string;
  onSend: (text: string, file: File | null) => Promise<void>;
  disabled?: boolean;
  attachedName?: string;
};

function ResumeAttachControl({
  onFile,
  onValidationError,
}: {
  onFile: (file: File | null) => void;
  onValidationError: (message: string) => void;
}) {
  const { state, actions } = useChatComposer();

  useEffect(() => {
    if (state.attachments.length > 1) {
      onValidationError("Attach one résumé at a time.");
      for (const extra of state.attachments.slice(1)) {
        actions.removeAttachment(extra.id);
      }
      return;
    }

    const file = state.attachments[0]?.file ?? null;
    if (file && file.size > RESUME_MAX_BYTES) {
      onValidationError("Résumé must be 5 MB or smaller.");
      actions.removeAttachment(state.attachments[0].id);
      onFile(null);
      return;
    }

    onFile(file);
    if (file) onValidationError("");
  }, [state.attachments, actions, onFile, onValidationError]);

  return (
    <ChatComposerAttachButton
      accept={RESUME_ACCEPT}
      multiple={false}
      label="Attach PDF or DOCX résumé"
      className={styles.astryxAttachButton}
    />
  );
}

export function TalChatComposer({
  id,
  onSend,
  disabled = false,
  attachedName,
}: TalChatComposerProps) {
  const [error, setError] = useState("");
  const [value, setValue] = useState("");
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [attachEpoch, setAttachEpoch] = useState(0);

  const onValidationError = useCallback((message: string) => {
    if (message) setError(message);
  }, []);

  const performSend = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed && !resumeFile) return;
      try {
        await onSend(trimmed, resumeFile);
        setError("");
        setValue("");
        setResumeFile(null);
        setAttachEpoch((epoch) => epoch + 1);
      } catch (caught) {
        const message =
          caught instanceof Error ? caught.message : "Could not send your message.";
        setError(message);
        // Astryx clears the field on submit; restore the draft after a failure.
        setValue(text);
      }
    },
    [onSend, resumeFile],
  );

  const canSend = Boolean(value.trim() || resumeFile) && !disabled;

  const drawer =
    resumeFile || attachedName ? (
      <div className={styles.astryxDrawer}>
        <ChatComposerAttachments className={styles.attachmentList} />
        {attachedName && !resumeFile ? (
          <p className={styles.attachment}>Résumé attached · {attachedName}</p>
        ) : null}
      </div>
    ) : undefined;

  return (
    <div className={styles.composerDock}>
      {error ? (
        <p role="alert" className={styles.error}>
          {error}
        </p>
      ) : null}
      <div className={styles.composerForm}>
        <LocalChatComposerProvider
          key={attachEpoch}
          disabled={disabled}
          onSubmit={async () => {}}
          canSubmit={() => false}
        >
          <ChatComposer
            id={id}
            className={styles.astryxComposer}
            density="compact"
            elevation="none"
            isDisabled={disabled}
            value={value}
            onChange={setValue}
            onSubmit={performSend}
            placeholder="Ask TAL about a role, your résumé, or your next move…"
            footerActions={
              <ResumeAttachControl
                onFile={setResumeFile}
                onValidationError={onValidationError}
              />
            }
            drawer={drawer}
            sendButton={
              <ChatSendButton
                isDisabled={!canSend}
                onSend={() => performSend(value)}
              />
            }
          />
        </LocalChatComposerProvider>
      </div>
    </div>
  );
}